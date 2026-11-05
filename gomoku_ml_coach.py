"""
Machine Learning-based Gomoku Post-Game Coach.

This module:
1. Loads and preprocesses game CSV files from the games/ folder.
2. Extracts features from move sequences.
3. Trains an XGBoost model to predict move quality and mistake patterns.
4. Generates human-like coaching summaries based on ML predictions.

The pipeline runs automatically after each game to provide personalized feedback.
"""

import os
import glob
import pickle
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import warnings
import xgboost as xgb 

warnings.filterwarnings("ignore")

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("Warning: XGBoost not installed. Install with: pip install xgboost")

# ============================================================================
# 1. DATA LOADING & PREPROCESSING
# ============================================================================

def load_game_csvs(games_folder: str = "games") -> pd.DataFrame:
    """
    Load all game CSV files from the games folder and combine them.
    
    Args:
        games_folder: Path to folder containing game_*.csv files.
    
    Returns:
        Combined DataFrame with all moves from all games.
    """
    csv_files = glob.glob(os.path.join(games_folder, "game_*.csv"))
    
    if not csv_files:
        print(f"No game CSV files found in {games_folder}")
        return pd.DataFrame()
    
    all_games = []
    for csv_file in csv_files:
        try:
            # Read CSV, skip metadata rows (first 3 rows are metadata)
            df = pd.read_csv(csv_file, skiprows=3)
            # Extract game metadata from filename or first rows
            all_games.append(df)
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")
            continue
    
    if not all_games:
        return pd.DataFrame()
    
    combined = pd.concat(all_games, ignore_index=True)
    return combined


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract ML-ready features from raw move data.
    
    Features:
    - move_number: Position in game (1-indexed)
    - move_phase: Opening (1-8), Midgame (9-25), Endgame (26+)
    - is_player_move: 1 if player's color, 0 otherwise
    - missed_win: 1 if player missed immediate win
    - missed_block: 1 if player missed critical block
    - weak_edge: 1 if move was on weak edge
    - low_value: 1 if move was low-value
    - good_move: 1 if move was strong
    - forced_move: 1 if move was forced (block)
    - risky_move: 1 if move was risky
    - move_quality_score: Heuristic score (0-100)
    - consecutive_mistakes: Count of consecutive mistakes before this move
    - threat_response_time: Moves since last threat (if applicable)
    
    Args:
        df: DataFrame with raw move data.
    
    Returns:
        DataFrame with extracted features.
    """
    df = df.copy()
    
    # Ensure required columns exist
    required_cols = [
        "move_no", "player", "row", "col", "elapsed_seconds",
        "good_move", "missed_win", "missed_block", "weak_edge", "low_value", "risky_move", "forced_move"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0
    
    # Move phase
    df["move_phase"] = pd.cut(
        df["move_no"],
        bins=[0, 8, 25, float("inf")],
        labels=["opening", "midgame", "endgame"],
        include_lowest=True
    )
    df["move_phase"] = df["move_phase"].astype(str)
    
    # Is player move (assume 'black' is player in single-player, or first player in PvP)
    # For now, we'll mark moves where player is the mover
    df["is_player_move"] = (df["player"] == "black").astype(int)
    
    # Board position features (simple heuristics)
    df["distance_from_center"] = np.sqrt(
        (df["row"] - 7.5) ** 2 + (df["col"] - 7.5) ** 2
    )
    df["is_edge_move"] = (
        (df["row"] < 2) | (df["row"] > 12) | (df["col"] < 2) | (df["col"] > 12)
    ).astype(int)
    
    # Move quality score (0-100)
    # Base score from position quality + event-based adjustments
    df["position_quality"] = 100 - (df["distance_from_center"] * 5)  # Center is better
    df["position_quality"] = df["position_quality"].clip(20, 100)  # Min 20, max 100
    
    df["move_quality_score"] = (
        df["position_quality"] * 0.4 +  # 40% weight on position
        df["good_move"] * 100 * 0.3 +   # 30% weight on good moves
        df["forced_move"] * 70 * 0.1 +  # 10% weight on forced moves
        (1 - df["missed_win"]) * 80 * 0.1 +  # 10% weight on not missing wins
        (1 - df["missed_block"]) * 75 * 0.1   # 10% weight on not missing blocks
    )
    df["move_quality_score"] = df["move_quality_score"].clip(0, 100)
    
    # Consecutive mistakes
    df["mistake_flag"] = (
        df["missed_win"] | df["missed_block"] | df["weak_edge"] | df["low_value"]
    ).astype(int)
    df["consecutive_mistakes"] = (
        df.groupby((df["mistake_flag"] == 0).cumsum())["mistake_flag"]
        .cumsum()
        .fillna(0)
        .astype(int)
    )
    
    # Threat response time (moves since last threat)
    df["threat_flag"] = (df["missed_block"] | df["forced_move"]).astype(int)
    df["threat_response_time"] = (
        df.groupby((df["threat_flag"] == 0).cumsum())
        .cumcount()
        .fillna(0)
        .astype(int)
    )
    
    return df


def prepare_training_data(df: pd.DataFrame, target_col: str = "move_quality_score") -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare features and target for XGBoost training.
    
    Args:
        df: DataFrame with extracted features.
        target_col: Column to predict.
    
    Returns:
        (X, y) tuple ready for training.
    """
    # Select feature columns
    feature_cols = [
        "move_no", "is_player_move", "missed_win", "missed_block", "weak_edge",
        "low_value", "good_move", "forced_move", "risky_move",
        "consecutive_mistakes", "threat_response_time", "distance_from_center",
        "is_edge_move", "elapsed_seconds"
    ]
    
    # Ensure all feature columns exist
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0
    
    X = df[feature_cols].fillna(0)
    y = df[target_col].fillna(0)
    
    return X, y


# ============================================================================
# 2. MODEL TRAINING & PERSISTENCE
# ============================================================================

def train_model(games_folder: str = "games", model_path: str = "gomoku_coach_xgb.pkl") -> Optional[xgb.XGBRegressor]:
    """
    Load game CSVs, extract features, and train XGBoost model.
    
    Args:
        games_folder: Path to games folder.
        model_path: Path to save trained model.
    
    Returns:
        Trained XGBRegressor model, or None if training fails.
    """
    if not XGBOOST_AVAILABLE:
        print("XGBoost not available. Skipping model training.")
        return None
    
    print("Loading game CSVs...")
    df = load_game_csvs(games_folder)
    
    if df.empty:
        print("No game data available for training.")
        return None
    
    print(f"Loaded {len(df)} moves from game CSVs.")
    
    print("Extracting features...")
    df = extract_features(df)
    
    print("Preparing training data...")
    X, y = prepare_training_data(df)
    
    if X.empty or y.empty:
        print("No training data available.")
        return None
    
    print(f"Training XGBoost model on {len(X)} samples...")
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0
    )
    
    model.fit(X, y, verbose=False)
    
    print(f"Model trained. Saving to {model_path}...")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    
    print("Model saved successfully.")
    return model


def load_model(model_path: str = "gomoku_coach_xgb.pkl") -> Optional[xgb.XGBRegressor]:
    """
    Load a pre-trained XGBoost model.
    
    Args:
        model_path: Path to saved model.
    
    Returns:
        Loaded model, or None if file doesn't exist.
    """
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}. Please train the model first.")
        return None
    
    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        print(f"Model loaded from {model_path}")
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
        return None


# ============================================================================
# 3. PREDICTION & FEATURE EXTRACTION
# ============================================================================

def predict_mistakes(game_csv_path: str, model_path: str = "gomoku_coach_xgb.pkl") -> Dict[str, Any]:
    """
    Predict move quality and extract key events from a single game CSV.
    
    Args:
        game_csv_path: Path to a single game CSV file.
        model_path: Path to trained model.
    
    Returns:
        Dictionary with predictions and extracted events.
    """
    if not XGBOOST_AVAILABLE:
        return {"error": "XGBoost not available"}
    
    # Load model
    model = load_model(model_path)
    if model is None:
        return {"error": "Model not found. Please train the model first."}
    
    # Load and preprocess game data
    try:
        df = pd.read_csv(game_csv_path, skiprows=3)
    except Exception as e:
        return {"error": f"Could not load game CSV: {e}"}
    
    df = extract_features(df)
    X, _ = prepare_training_data(df)
    
    # Predict move quality scores
    predictions = model.predict(X)
    df["predicted_quality"] = predictions
    
    # Extract key events
    key_events = extract_key_events(df)
    
    return {
        "game_csv": game_csv_path,
        "predictions": predictions,
        "dataframe": df,
        "key_events": key_events,
        "error": None
    }


def extract_key_events(df: pd.DataFrame) -> Dict[str, List[Dict]]:
    """
    Extract high-level events from game data for storytelling.
    
    Events include:
    - Major mistakes (missed wins, missed blocks)
    - Strong moves
    - Turning points
    - Phase transitions
    
    Args:
        df: DataFrame with move data and predictions.
    
    Returns:
        Dictionary of event lists.
    """
    events = {
        "major_mistakes": [],
        "strong_moves": [],
        "turning_points": [],
        "phase_summary": {}
    }
    
    # Ensure mistake columns are numeric (they might be strings from CSV)
    for col in ["missed_win", "missed_block", "good_move"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Identify major mistakes
    mistakes = df[
        (df["missed_win"] == 1) | (df["missed_block"] == 1)
    ]
    for idx, row in mistakes.iterrows():
        events["major_mistakes"].append({
            "move_no": int(row["move_no"]),
            "type": "missed_win" if row["missed_win"] == 1 else "missed_block",
            "position": (int(row["row"]), int(row["col"])),
            "quality_score": float(row.get("predicted_quality", 0))
        })
    
    # Identify strong moves
    strong = df[df["good_move"] == 1]
    for idx, row in strong.iterrows():
        events["strong_moves"].append({
            "move_no": int(row["move_no"]),
            "position": (int(row["row"]), int(row["col"])),
            "quality_score": float(row.get("predicted_quality", 100))
        })
    
    # Identify turning points (sudden quality changes)
    if len(df) > 2:
        df["quality_change"] = df.get("predicted_quality", df.get("move_quality_score", 0)).diff().abs()
        turning = df[df["quality_change"] > df["quality_change"].quantile(0.75)]
        for idx, row in turning.iterrows():
            events["turning_points"].append({
                "move_no": int(row["move_no"]),
                "quality_change": float(row["quality_change"]),
                "position": (int(row["row"]), int(row["col"]))
            })
    
    # Phase summary
    for phase in ["opening", "midgame", "endgame"]:
        phase_data = df[df["move_phase"] == phase]
        if not phase_data.empty:
            avg_quality = phase_data.get("predicted_quality", phase_data.get("move_quality_score", 0)).mean()
            mistake_count = (
                phase_data["missed_win"].sum() + phase_data["missed_block"].sum()
            )
            events["phase_summary"][phase] = {
                "avg_quality": float(avg_quality),
                "mistake_count": int(mistake_count),
                "move_count": len(phase_data)
            }
    
    return events


# ============================================================================
# 4. STORY GENERATION (ML → NLP PIPELINE)
# ============================================================================

def generate_story_summary(key_events: Dict[str, Any], winner: Optional[str] = None) -> str:
    """
    Convert ML predictions and extracted events into a human-like coaching story.
    
    Args:
        key_events: Dictionary of events from extract_key_events().
        winner: Who won ("You", "Computer", "Player 1", "Player 2", etc.)
    
    Returns:
        Human-friendly coaching narrative.
    """
    story_parts = []
    
    # Opening
    if winner:
        if winner in ("You", "Player 1", "Player 2"):
            story_parts.append(f"Great match! You played well and came out on top.")
        else:
            story_parts.append(f"Tough loss, but there's a lot to learn from this game.")
    else:
        story_parts.append("Here's your game analysis:")
    
    # Phase-by-phase summary
    phase_summary = key_events.get("phase_summary", {})
    
    if "opening" in phase_summary:
        opening = phase_summary["opening"]
        quality = opening["avg_quality"]
        if quality > 75:
            story_parts.append(
                f"Your opening was solid, with an average move quality of {quality:.0f}/100. "
                "You set up a good foundation for the midgame."
            )
        elif quality > 50:
            story_parts.append(
                f"In the opening, you played cautiously with a quality score of {quality:.0f}/100. "
                "Nothing too risky, but you could have been more aggressive."
            )
        else:
            story_parts.append(
                f"Your opening moves (quality: {quality:.0f}/100) were a bit passive. "
                "Consider playing closer to the center earlier."
            )
    
    # Major mistakes
    major_mistakes = key_events.get("major_mistakes", [])
    if major_mistakes:
        story_parts.append(f"\nYou had {len(major_mistakes)} critical moment(s) where you slipped:")
        for mistake in major_mistakes[:3]:  # Top 3 mistakes
            move_no = mistake["move_no"]
            mtype = mistake["type"]
            row, col = mistake["position"]
            if mtype == "missed_win":
                story_parts.append(
                    f"  • Move {move_no} at ({row},{col}): You missed an immediate winning opportunity. "
                    "Always scan for your own winning moves first!"
                )
            else:  # missed_block
                story_parts.append(
                    f"  • Move {move_no} at ({row},{col}): You overlooked a critical block. "
                    "Your opponent was threatening, and you didn't respond in time."
                )
    
    # Strong moves
    strong_moves = key_events.get("strong_moves", [])
    if strong_moves:
        story_parts.append(f"\nYou also had {len(strong_moves)} strong move(s):")
        for move in strong_moves[:2]:  # Top 2 strong moves
            move_no = move["move_no"]
            row, col = move["position"]
            story_parts.append(
                f"  • Move {move_no} at ({row},{col}): Excellent tactical awareness. "
                "This move showed good board control."
            )
    
    # Midgame summary
    if "midgame" in phase_summary:
        midgame = phase_summary["midgame"]
        quality = midgame["avg_quality"]
        mistakes = midgame["mistake_count"]
        if mistakes > 2:
            story_parts.append(
                f"\nMidgame was where things got tricky. You made {mistakes} mistakes during this phase. "
                "This is where most games are decided—focus on threat detection here."
            )
        elif quality > 70:
            story_parts.append(
                f"\nYour midgame was strong (quality: {quality:.0f}/100). "
                "You maintained pressure and adapted well to your opponent's moves."
            )
    
    # Endgame summary
    if "endgame" in phase_summary:
        endgame = phase_summary["endgame"]
        quality = endgame["avg_quality"]
        if quality > 80:
            story_parts.append(
                f"\nIn the endgame, you closed out strong with a quality score of {quality:.0f}/100. "
                "You finished decisively."
            )
        elif quality > 50:
            story_parts.append(
                f"\nThe endgame was close (quality: {quality:.0f}/100). "
                "You had chances but didn't capitalize fully."
            )
    
    # Turning points
    turning_points = key_events.get("turning_points", [])
    if turning_points:
        story_parts.append(
            f"\nThere were {len(turning_points)} key turning point(s) in this game. "
            "These moments shifted the momentum significantly."
        )
    
    # Closing advice
    story_parts.append("\n" + "=" * 60)
    if major_mistakes:
        story_parts.append(
            "KEY TAKEAWAY: Focus on scanning the board for both winning moves and defensive blocks. "
            "These two things alone will improve your game significantly."
        )
    else:
        story_parts.append(
            "KEY TAKEAWAY: You played a clean game with few major mistakes. "
            "Keep building on this consistency and look for more aggressive opportunities."
        )
    
    return "\n".join(story_parts)


# ============================================================================
# 5. COACH REPLY (CHATBOT-STYLE DELIVERY)
# ============================================================================

def coach_reply(game_csv_path: str, winner: Optional[str] = None, model_path: str = "gomoku_coach_xgb.pkl") -> str:
    """
    Main entry point: Load game, predict, extract events, and generate coaching story.
    
    This function runs automatically after each game and returns a human-friendly summary.
    
    Args:
        game_csv_path: Path to the game CSV file.
        winner: Who won the game.
        model_path: Path to trained XGBoost model.
    
    Returns:
        Coaching story as a string.
    """
    # Check if model exists before proceeding
    if not os.path.exists(model_path):
        return "ML Coach: Model not found. Play more games to train the ML model, then check back for personalized analysis!"
    
    # Predict and extract events
    result = predict_mistakes(game_csv_path, model_path)
    
    if result.get("error"):
        if "Could not load or train model" in result["error"]:
            return "ML Coach: Model not available. Play more games to train the ML model, then check back for personalized analysis!"
        return f"Coach: I couldn't analyze this game right now ({result['error']}). Try again later!"
    
    key_events = result.get("key_events", {})
    
    # Generate story
    story = generate_story_summary(key_events, winner)
    
    # Wrap in coach persona
    coach_message = f"🎯 COACH'S ANALYSIS:\n\n{story}"
    
    return coach_message


# ============================================================================
# 6. UTILITY FUNCTIONS
# ============================================================================

def retrain_model_if_needed(games_folder: str = "games", model_path: str = "gomoku_coach_xgb.pkl", min_games: int = 3) -> bool:
    """
    Retrain the model if there are new games since last training.
    
    Args:
        games_folder: Path to games folder.
        model_path: Path to model file.
        min_games: Minimum number of games needed to train.
    
    Returns:
        True if model was retrained, False otherwise.
    """
    csv_files = glob.glob(os.path.join(games_folder, "game_*.csv"))
    
    if len(csv_files) < min_games:
        print(f"Not enough games to train ({len(csv_files)} < {min_games}). Skipping retraining.")
        return False
    
    if not os.path.exists(model_path):
        print("Model doesn't exist. Training new model...")
        train_model(games_folder, model_path)
        return True
    
    # Check if any new games are newer than the model
    model_mtime = os.path.getmtime(model_path)
    for csv_file in csv_files:
        if os.path.getmtime(csv_file) > model_mtime:
            print("New games detected. Retraining model...")
            train_model(games_folder, model_path)
            return True
    
    return False


if __name__ == "__main__":
    # Example usage
    print("Gomoku ML Coach - Example Usage\n")
    
    # Train model
    print("Step 1: Training model...")
    model = train_model()
    
    if model:
        # Predict on a recent game
        print("\nStep 2: Analyzing a game...")
        game_files = glob.glob("games/game_single_*.csv")
        if game_files:
            latest_game = max(game_files, key=os.path.getctime)
            print(f"Analyzing: {latest_game}")
            
            story = coach_reply(latest_game, winner="You")
            print("\n" + story)
