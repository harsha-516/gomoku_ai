# 🎮 Gomoku AI Game

A full-featured **Gomoku (Five-in-a-Row) game** with intelligent AI opponent, real-time move suggestions, and machine learning-powered coaching. Built with Python and Tkinter for an interactive learning experience.

---

## 📋 Table of Contents

- [Features](#features)
- [Project Overview](#project-overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Game Modes](#game-modes)
- [How to Play](#how-to-play)
- [AI Difficulty Levels](#ai-difficulty-levels)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Core Components](#core-components)
- [Game Analysis & Coaching](#game-analysis--coaching)
- [Data & Machine Learning](#data--machine-learning)
- [Requirements](#requirements)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

### Gameplay
- **15×15 Gomoku Board** - Classic game configuration
- **Two Game Modes**:
  - Single Player vs AI with adjustable difficulty
  - Player vs Player (local multiplayer)
- **Real-time Move Suggestions** - AI-powered hints during gameplay
- **Game Timer** - Tracks total game duration
- **Move History** - Complete move logging and replay capability
- **Win Detection** - Automatic 5-in-a-row detection

### AI & Strategy
- **Three AI Difficulty Levels**:
  - **Easy**: Random valid moves
  - **Medium**: Tactical play with depth-3 search
  - **Hard**: Strategic play with depth-5 minimax search
- **Advanced Evaluation**: Threats, patterns, and board control assessment
- **Smart Candidate Generation**: Focuses on moves near existing pieces

### Coaching & Analysis
- **Rule-based Game Analysis**:
  - Detects missed winning moves
  - Identifies failed defensive plays
  - Analyzes board strategy
  - Provides actionable feedback
- **ML-powered Coaching**:
  - Machine learning model trained on game data
  - Personalized move quality predictions
  - Pattern recognition for common mistakes
  - Auto-retraining on new games

### User Interface
- **Modern Tkinter Design** - Clean, responsive layout
- **Navigation Menu** - Seamless switching between modes
- **Move Suggestions Overlay** - Interactive hint display
- **Game Statistics** - Score tracking and performance metrics
- **Inactivity Alerts** - Reminds players of long pauses

### Data Tracking
- **Automatic Game Recording** - CSV format with timestamps
- **Game Analytics** - Stored in `games/` folder for analysis
- **Performance Metrics** - Tracks wins, losses, and strategy effectiveness

---

## 🎯 Project Overview

Gomoku (also known as Five-in-a-Row or Renju) is an abstract strategy board game where two players take turns placing stones on a 15×15 board. The first player to create an unbroken line of five stones horizontally, vertically, or diagonally wins.

This project combines:
1. **Classic Game Logic** - Complete Gomoku rules implementation
2. **Intelligent AI** - Minimax with alpha-beta pruning
3. **Real-time Suggestions** - In-game move recommendations
4. **Coaching System** - Dual analysis (rule-based + ML-based)
5. **Learning Platform** - Improve through detailed feedback

---

## 📦 Installation

### Prerequisites
- Python 3.8+ (with tkinter built-in on Windows)
- pip (Python package installer)

### Linux/Mac Users
If tkinter is missing:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS
brew install python-tk@3.x  # where x is your Python version
```

### Step 1: Clone the Repository
```bash
git clone https://github.com/karthik14344/Gomuku.git
cd Gomuku
```

### Step 2: Create Virtual Environment (Optional but Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation
```bash
python check_dependencies.py
```

Expected output:
```
============================================================
Gomoku ML Coach - Dependency Checker
============================================================

✓ pandas              - OK
✓ numpy               - OK
✓ xgboost             - OK
✓ scikit-learn        - OK
✓ python-dateutil     - OK
✓ tkinter             - OK

============================================================
✓ All dependencies are installed!
You can now run: python main.py
```

---

## 🚀 Quick Start

### Run the Game
```bash
python main.py
```

The GUI will open showing the home page with three options:
1. **Single Player** - Play against the AI
2. **Player vs Player** - Local multiplayer
3. **How To Play** - View game rules and tutorials

---

## 🎮 Game Modes

### Single Player (vs AI)

**Features:**
- Choose AI difficulty before starting
- Receive move suggestions anytime during play
- AI responds intelligently based on difficulty level
- Automatic game saving and analysis

**Workflow:**
1. Click "Single Player" from home
2. Select difficulty (Easy/Medium/Hard)
3. Place black stones (you always go first)
4. Computer responds with white stones
5. Game ends when someone gets 5-in-a-row
6. Receive coaching feedback on your performance

**Tips:**
- Use suggestions liberally to learn strategy
- Try Hard difficulty for maximum challenge
- Play multiple games to improve your ranking

### Player vs Player

**Features:**
- Local multiplayer on single machine
- Players alternate turns
- Both players get move suggestions
- Full game history and analysis

**Workflow:**
1. Click "Player vs Player" from home
2. Black player places first stone
3. White player responds
4. Continue alternating until win condition
5. Post-game analysis available for both players

---

## 📚 How To Play

### Basic Rules
1. **Board**: 15×15 grid (225 squares)
2. **Starting**: Black player goes first (always center-ish area)
3. **Taking Turns**: Players alternate placing one stone per turn
4. **Winning**: First to create 5+ consecutive stones in any direction wins
5. **Directions**: Horizontal, vertical, or diagonal lines count

### Valid Directions for Winning
```
Horizontal:   ●●●●●
Vertical:     ●
              ●
              ●
              ●
              ●

Diagonal:     ●
                ●
                  ●
                    ●
                      ●

Anti-diagonal: ●
               ●
               ●
               ●
               ●
```

### Strategic Tips
- **Center Control**: Control the board center for tactical advantage
- **Create Threats**: Build multiple winning paths simultaneously
- **Block Opponents**: Stop their 4-in-a-row patterns
- **Pattern Recognition**: Watch for sequences of 3-4 stones
- **Early Game**: Start near center; expand outward
- **Mid Game**: Create multiple threats (opponent can't block all)
- **End Game**: Convert threats into winning moves

### Using Suggestions
- **Green Highlight**: Top recommended moves
- **⭐ WIN**: Move wins immediately
- **🛡️ BLOCK**: Defensive move to stop opponent's win
- **Score Number**: Move quality assessment (higher = better)

---

## 🤖 AI Difficulty Levels

### Easy
- **Strategy**: Random valid moves from candidates
- **Search Depth**: None (no lookahead)
- **Best For**: Learning basic rules
- **Skill Level**: Beginner
- **Decision Time**: ~10ms

### Medium
- **Strategy**: Minimax with depth-3 search
- **Evaluation**: Threat assessment, board control scoring
- **Best For**: Intermediate players practicing strategy
- **Skill Level**: Intermediate
- **Decision Time**: ~500ms-1s

### Hard
- **Strategy**: Minimax with depth-5 search + alpha-beta pruning
- **Evaluation**: Advanced threat detection, pattern recognition
- **Best For**: Advanced players seeking challenge
- **Skill Level**: Advanced
- **Decision Time**: ~2-5s

### AI Decision Algorithm
```
1. Generate candidate moves (moves near existing stones)
2. For each candidate, evaluate:
   - Can I win immediately?
   - Can opponent win next move? (Block if yes)
   - How many threats does this create?
   - What's the board control score?
3. Score each move based on evaluation
4. Apply difficulty filter:
   - Easy: Random selection
   - Medium: Top moves + some randomness
   - Hard: Deterministic best move
5. Execute selected move
```

---

## 🏗️ Architecture

### High-Level Design
```
┌─────────────────────────────────────────┐
│         Tkinter GUI Layer               │
│  (main.py, single_player.py, etc)      │
├─────────────────────────────────────────┤
│      Game Logic & UI Controller         │
│  (Game state, move validation, display) │
├─────────────────────────────────────────┤
│    AI Engine & Algorithms               │
│  (gomoku_ai.py - evaluation & search)   │
├─────────────────────────────────────────┤
│    Analysis & Coaching Systems          │
│  (Rule-based & ML coaching)             │
├─────────────────────────────────────────┤
│    Data Layer                           │
│  (CSV files, game history)              │
└─────────────────────────────────────────┘
```

### Data Flow
```
Player Input
    ↓
Validate Move (gomoku_ai.py)
    ↓
Execute Move → Update Board
    ↓
Check Win Condition
    ├─ No Win
    │  ↓
    │  Generate AI Move (gomoku_ai.py)
    │  ↓
    │  Update Board
    │  ↓
    │  Check Win Condition
    │
    └─ Win/Draw
       ↓
       Record Game (CSV)
       ↓
       Analyze Game
       ├─ Rule-based (gomoku_coach.py)
       └─ ML-based (gomoku_ml_coach.py)
       ↓
       Provide Coaching Feedback
       ↓
       Retrain ML Model (if needed)
```

---

## 📁 Project Structure

```
Gomuku/
├── main.py                      # Entry point, home page GUI
├── single_player.py             # Single player vs AI game mode
├── player_vs_player.py          # Local multiplayer mode
├── how_to_play.py              # Tutorial and rules page
│
├── gomoku_ai.py                 # Core AI algorithms
│   ├── Board analysis
│   ├── Minimax search
│   ├── Threat detection
│   └── Move evaluation
│
├── gomoku_coach.py              # Rule-based game analysis
│   ├── Move analysis
│   ├── Mistake detection
│   └── Feedback generation
│
├── gomoku_ml_coach.py           # ML-powered coaching
│   ├── Feature extraction
│   ├── Model training
│   └── Prediction & feedback
│
├── suggestion_overlay.py        # Real-time move suggestions UI
│
├── check_dependencies.py        # Dependency verification script
├── requirements.txt             # Python package dependencies
│
├── games/                       # Game history (auto-generated)
│   ├── game_single_20251118_124236.csv
│   ├── game_pvp_20251118_124236.csv
│   └── ... (more game records)
│
├── __pycache__/                 # Python cache (auto-generated)
│
└── README.md                    # This file
```

---

## 🔧 Core Components

### 1. gomoku_ai.py (453 lines)

**Board Analysis Functions:**
```python
get_empty_cells(state)          # Returns all empty positions
candidate_moves(state)          # Smart move candidates
neighbors_exist(state, r, c)    # Checks surrounding pieces
is_win_at(state, r, c, color)   # Detects 5-in-a-row
```

**Evaluation Functions:**
```python
evaluate(state, perspective)    # Board score calculation
score_color(state, color)       # Threat & pattern scoring
count_threat_level(...)         # Measures piece sequences
is_open_threat(...)             # Identifies dangerous patterns
```

**AI Algorithms:**
```python
ai_easy()                       # Random move selection
ai_search()                     # Minimax with pruning
suggest_moves()                 # Move recommendations
```

**Scoring System:**
- 5 in a row: **100,000** points
- Open 4: **10,000** points
- Closed 4: **3,000** points
- Open 3: **1,000** points
- Closed 3: **200** points
- Open 2: **50** points

### 2. single_player.py (1046 lines)

**Main Classes:**
```python
class GomokuGamePage:
    # Single player game controller
    # Handles UI, AI moves, game state
```

**Key Methods:**
- `create_game_board()` - Renders 15×15 board
- `on_board_click()` - Processes player moves
- `ai_move_thread()` - Executes AI move (non-blocking)
- `save_game()` - Records game to CSV
- `end_game()` - Calls coaching system

### 3. gomoku_coach.py (287 lines)

**Analysis Functions:**
```python
analyze_game_rule_based(move_log, difficulty)
    # Returns: list of move analysis with feedback

summarize_gomoku_game(move_log, difficulty)
    # Returns: human-readable coaching summary
```

**Detects:**
- ✓ Missed winning moves
- ✓ Failed defensive blocks
- ✓ Weak edge plays
- ✓ Low-value moves
- ✓ Pattern mistakes

### 4. gomoku_ml_coach.py (632 lines)

**ML Pipeline:**
```python
load_game_csvs()                # Load historical games
extract_features()              # Feature engineering
train_model()                   # XGBoost training
coach_reply()                   # Generate ML feedback
retrain_model_if_needed()       # Auto-training trigger
```

**Features Extracted:**
- Move position (row, col)
- Board state patterns
- Threat levels
- Distance to edges
- Move sequence context
- Game phase (opening/mid/end)

---

## 📊 Game Analysis & Coaching

### Rule-Based Coaching (gomoku_coach.py)

Analyzes each move using heuristic rules:

1. **Win Detection**
   ```
   Is this move a winning move?
   If yes: Suggest player should have played it!
   ```

2. **Block Detection**
   ```
   Is the opponent threatening a win?
   If yes: This move should block it!
   ```

3. **Edge Analysis**
   ```
   Is the move too close to board edge?
   Edge moves reduce strategic flexibility.
   ```

4. **Value Assessment**
   ```
   Score move by threats created and opponent threats stopped
   Compare to suggestions to rate move quality
   ```

**Output Example:**
```
Move 5: (7, 7) by Black
✗ Mistake: Missed winning opportunity at (8, 8)
Better moves: [(8,8,'win'), (6,6,'score'), (9,9,'block')]
Coaching: "Watch for immediate winning patterns - they're the highest priority!"
```

### ML-Powered Coaching (gomoku_ml_coach.py)

Machine learning analysis on move patterns:

1. **Feature Extraction**
   - Board state representation
   - Move position features
   - Sequence context
   - Game phase indicators

2. **Model Training**
   - Algorithm: XGBoost (Gradient Boosting)
   - Target: Move quality (win/block/score/mistake)
   - Training: Auto-runs after 5+ new games

3. **Prediction & Feedback**
   ```
   For each player move:
   - Predict if it's a quality move
   - Identify mistake patterns
   - Generate personalized feedback
   - Track improvement over time
   ```

4. **Continuous Improvement**
   - Auto-retrain when new games available
   - Adapt to player skill level
   - Improve accuracy over time

---

## 📈 Data & Machine Learning

### Game Recording Format

Each game saves to `games/game_single_TIMESTAMP.csv`:

```csv
move_number,player_color,row,col,board_state,difficulty,timestamp,move_quality
1,black,7,7,"[[None]*15 for _ in range(15)]",Hard,2025-11-18 12:42:36.123456,None
2,white,8,8,"[[None,...],...]",Hard,2025-11-18 12:42:40.456789,score
3,black,6,6,"[[None,...],...]",Hard,2025-11-18 12:42:45.789123,win
...
```

### Data Usage

1. **Game History** - Review past games
2. **Performance Tracking** - Win rate, strategy patterns
3. **Model Training** - ML coaching system learns from games
4. **Pattern Analysis** - Identify common mistakes
5. **Skill Assessment** - Difficulty recommendations

### ML Model Details

**Model Type:** XGBoost Classifier
**Input Features:** 15+ engineered features from board state
**Output Classes:** win, block, score, mistake
**Training Data:** Historical game records
**Retraining:** Automatic when 5+ new games recorded
**Prediction Time:** <100ms per move

---

## 📋 Requirements

### Python Packages
```
pandas>=1.3.0           # Data manipulation
numpy>=1.21.0           # Numerical computing
xgboost>=1.5.0          # ML model
scikit-learn>=0.24.0    # Feature engineering
python-dateutil>=2.8.0  # Timestamp handling
```

### System Requirements
- **Python**: 3.8+
- **RAM**: 512MB minimum (1GB+ recommended)
- **Disk**: 50MB (+ game data)
- **Display**: 1024x768 minimum (1366x768+ recommended)
- **OS**: Windows, Linux, macOS

### Install All Dependencies
```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install pandas numpy xgboost scikit-learn python-dateutil
```

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'tkinter'"

**Solution:**
```bash
# Windows: Usually pre-installed, reinstall Python with tkinter checked

# Ubuntu/Debian:
sudo apt-get install python3-tk

# macOS:
brew install python-tk@3.x
```

### Issue: XGBoost not loading

**Solution:**
```bash
# Reinstall XGBoost
pip install xgboost --force-reinstall
```

### Issue: Game runs slowly

**Possible Causes:**
- Hard AI difficulty with slow computer
- Too many background processes
- Large game history (>1000 games)

**Solutions:**
1. Switch to Medium difficulty
2. Close other applications
3. Delete old games from `games/` folder (backup first)

### Issue: No suggestions appearing

**Solutions:**
1. Ensure `suggestion_overlay.py` is in project directory
2. Check that `gomoku_ai.py` has `suggest_moves()` function
3. Verify AI engine is running without errors
4. Check console for exception messages

### Issue: ML Coaching not working

**Solutions:**
1. Ensure `xgboost` is installed: `pip install xgboost`
2. Play 5+ games to train model
3. Check `games/` folder has game CSVs
4. Restart application after playing games

### Issue: Application crashes on startup

**Debug Steps:**
```bash
# Run dependency checker
python check_dependencies.py

# Run with debug mode (show errors)
python -u main.py

# Check Python version
python --version  # Should be 3.8+
```

---

## 🤝 Contributing

Contributions are welcome! Here's how to help:

### Fork & Clone
```bash
git clone https://github.com/karthik14344/Gomuku.git
cd Gomuku
```

### Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### Make Changes
- Follow existing code style
- Add comments for complex logic
- Test thoroughly before committing

### Commit & Push
```bash
git add .
git commit -m "Add: Brief description of changes"
git push origin feature/your-feature-name
```

### Create Pull Request
- Describe your changes clearly
- Reference any related issues
- Include test results if applicable

### Areas for Contribution
- [ ] Additional AI algorithms (MCTS, Neural Networks)
- [ ] Extended board sizes (19×19, 13×13)
- [ ] Network multiplayer support
- [ ] Mobile version
- [ ] Performance optimization
- [ ] UI improvements
- [ ] Documentation
- [ ] Bug fixes

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

### You are free to:
- ✓ Use commercially
- ✓ Modify the code
- ✓ Distribute copies
- ✓ Use privately

### You must:
- ✓ Include license and copyright notice

---

## 📞 Support

- **GitHub Issues**: Report bugs and request features
- **Email**: (Add your contact if desired)
- **Wiki**: Check project wiki for detailed guides

---

## 🏆 Acknowledgments

- Gomoku rules and strategy inspiration
- XGBoost team for ML model
- Python community for excellent libraries
- All contributors and testers

---

## 🚀 Future Roadmap

- [ ] Online multiplayer support
- [ ] Advanced statistics dashboard
- [ ] Game replay viewer
- [ ] AI personality profiles
- [ ] Mobile app version
- [ ] Tournament mode
- [ ] Difficulty curve learning
- [ ] Opening library integration
- [ ] Cloud save support
- [ ] Discord bot integration

---

## 📝 Changelog

### Version 1.0 (Current)
- ✓ Core Gomoku gameplay
- ✓ Single player vs AI (3 difficulties)
- ✓ Local multiplayer (Player vs Player)
- ✓ Real-time move suggestions
- ✓ Rule-based game coaching
- ✓ ML-powered coaching system
- ✓ Game history and recording
- ✓ Modern Tkinter GUI
- ✓ Auto-retraining ML model

### Planned for v1.1
- Network multiplayer
- Extended statistics
- Custom board sizes
- Performance improvements

---

## 📞 Questions?

Feel free to open an issue on GitHub for:
- Bug reports
- Feature requests
- Installation help
- Usage questions

---

**Enjoy the game and happy learning! 🎮✨**

Made with ❤️ by the Gomoku AI Project Team
