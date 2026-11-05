"""Builds analysis/gomoku_analysis.ipynb.  Run from the project root:

    python analysis/build_notebook.py
    jupyter nbconvert --to notebook --execute --inplace analysis/gomoku_analysis.ipynb
"""

import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

nb.cells = [
    md("# Intelligent Gomoku - Experimental Analysis\n\n"
       "This notebook analyses the data produced by `benchmark.py` (AI vs AI experiments) and by "
       "human games recorded in `games/`. It answers the questions from the project synopsis:\n\n"
       "1. How much does **alpha-beta pruning** and **move ordering** reduce the number of game states searched?\n"
       "2. How do the agents (Random, Rule-Based, Minimax, Alpha-Beta, Expert) compare in **playing strength** "
       "and **decision time**?\n"
       "3. What do the recorded **human games** tell us about common mistakes?"),
    code("import os, glob\n"
         "import pandas as pd\n"
         "import matplotlib.pyplot as plt\n"
         "ROOT = '..' if os.path.basename(os.getcwd()) == 'analysis' else '.'\n"
         "R = os.path.join(ROOT, 'results')\n"
         "eff = pd.read_csv(os.path.join(R, 'search_efficiency.csv'))\n"
         "games = pd.read_csv(os.path.join(R, 'tournament_games.csv'))\n"
         "moves = pd.read_csv(os.path.join(R, 'tournament_moves.csv'))\n"
         "standings = pd.read_csv(os.path.join(R, 'standings.csv'))\n"
         "print(f'{len(eff)} search measurements, {len(games)} tournament games, {len(moves)} recorded AI moves')"),

    md("## 1. Search efficiency: Minimax vs Alpha-Beta\n\n"
       "Every algorithm searched the **same test positions** with the **same candidate moves** and the same "
       "heuristic, so the only difference is pruning and move ordering."),
    code("pivot = eff.pivot_table(index='depth', columns='algorithm', values='nodes', aggfunc='mean').round(0)\n"
         "pivot = pivot[['Minimax', 'Alpha-Beta (unordered)', 'Alpha-Beta (ordered)']]\n"
         "pivot"),
    code("saving = (1 - pivot.div(pivot['Minimax'], axis=0)) * 100\n"
         "print('States saved compared with plain minimax (%):')\n"
         "saving.round(1)"),
    code("t = eff.pivot_table(index='depth', columns='algorithm', values='time_ms', aggfunc='mean').round(1)\n"
         "print('Average time per decision (ms):')\n"
         "t[['Minimax', 'Alpha-Beta (unordered)', 'Alpha-Beta (ordered)']]"),
    code("agree = eff.groupby('depth')['same_value_as_minimax'].mean() * 100\n"
         "print('Positions where all three algorithms returned the same minimax value (%):')\n"
         "print(agree.to_string())"),
    code("colors = {'Minimax': '#2a78d6', 'Alpha-Beta (unordered)': '#eb6834', 'Alpha-Beta (ordered)': '#1baf7a'}\n"
         "ax = pivot.plot(marker='o', logy=True, figsize=(7, 4), color=[colors[c] for c in pivot.columns], linewidth=2)\n"
         "ax.set_xlabel('Search depth (plies)'); ax.set_ylabel('States explored (log)')\n"
         "ax.set_title('Game states explored per decision', loc='left')\n"
         "ax.spines[['top', 'right']].set_visible(False); ax.grid(axis='y', alpha=.3)\n"
         "plt.show()"),
    md("**Observation.** Alpha-beta returns exactly the same value as minimax (the agreement check above) "
       "while visiting far fewer states, and the saving grows with depth. Good move ordering "
       "(searching wins, blocks and strong threats first) multiplies the effect, which is why the ordered "
       "version is the one used by the Hard and Expert levels."),

    md("## 2. Tournament: playing strength vs computational cost"),
    code("standings.set_index('agent')"),
    code("def score(row_agent, col_agent):\n"
         "    g = games[((games.black == row_agent) & (games.white == col_agent)) |\n"
         "              ((games.black == col_agent) & (games.white == row_agent))]\n"
         "    if g.empty: return None\n"
         "    pts = (g.winner_agent == row_agent).sum() + 0.5 * (g.winner_agent == 'Draw').sum()\n"
         "    return round(100 * pts / len(g))\n"
         "names = list(standings.agent)\n"
         "h2h = pd.DataFrame({c: [score(r, c) if r != c else None for r in names] for c in names}, index=names)\n"
         "print('Head-to-head score % (row agent vs column agent):')\n"
         "h2h"),
    code("fig, ax = plt.subplots(figsize=(7, 4))\n"
         "palette = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4']\n"
         "for i, r in standings.iterrows():\n"
         "    ax.scatter(max(r.avg_ms_per_move, 0.05), r.win_rate * 100, s=120, color=palette[i % 5], zorder=3)\n"
         "    ax.annotate(r.agent, (max(r.avg_ms_per_move, 0.05), r.win_rate * 100), xytext=(8, 4), textcoords='offset points')\n"
         "ax.set_xscale('log'); ax.set_xlabel('Average thinking time per move (ms, log)'); ax.set_ylabel('Win rate (%)')\n"
         "ax.set_title('Strength vs cost', loc='left'); ax.spines[['top', 'right']].set_visible(False); ax.grid(alpha=.3)\n"
         "plt.show()"),
    code("games['pairing'] = games[['black', 'white']].apply(lambda r: ' vs '.join(sorted(r)), axis=1)\n"
         "print('Average game length (moves) by pairing:')\n"
         "games.groupby('pairing')['moves'].mean().sort_values().round(1)"),
    code("print('Why the agents moved (top reasons per agent):')\n"
         "moves.groupby('agent')['reason'].value_counts().groupby(level=0).head(4)"),
    code("print('States explored per move as the game progresses (Alpha-Beta and Expert):')\n"
         "sub = moves[moves.agent.isin(['Alpha-Beta', 'Expert'])].copy()\n"
         "sub['phase'] = pd.cut(sub.move_no, [0, 10, 20, 30, 225], labels=['1-10', '11-20', '21-30', '31+'])\n"
         "sub.pivot_table(index='phase', columns='agent', values='nodes', aggfunc='mean', observed=False).round(0)"),

    md("## 3. Human games recorded by the GUI\n\n"
       "Every finished Single-Player game is saved to `games/` with the rule-based coach's labels per move."),
    code("rows = []\n"
         "for f in sorted(glob.glob(os.path.join(ROOT, 'games', 'game_*.csv'))):\n"
         "    meta = pd.read_csv(f, nrows=1)\n"
         "    mv = pd.read_csv(f, skiprows=3)\n"
         "    mv['file'] = os.path.basename(f); mv['mode'] = meta['mode'][0]; mv['winner'] = meta['winner'][0]\n"
         "    rows.append(mv)\n"
         "human = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()\n"
         "summary = human.groupby('file').agg(mode=('mode', 'first'), winner=('winner', 'first'), moves=('move_no', 'max'))\n"
         "print(f'{len(summary)} recorded games')\n"
         "summary.groupby(['mode', 'winner']).size().rename('games')"),
    code("flags = ['good_move', 'missed_win', 'missed_block', 'weak_edge', 'low_value', 'risky_move', 'forced_move']\n"
         "flags = [f for f in flags if f in human.columns]\n"
         "print('How often each label appears in the analysed (human) moves:')\n"
         "(human[flags].apply(pd.to_numeric, errors='coerce').fillna(0).sum()\n"
         " .sort_values(ascending=False).rename('count'))"),
    md("## 4. A dataset for machine learning\n\n"
       "`results/tournament_moves.csv` stores, for every AI move, the full board after the move "
       "(`board_after`, 225 characters), who moved, the search statistics and the reason. "
       "This is the starting point for the future ML coaching described in the synopsis, e.g. "
       "learning to predict the strong agent's move from the board."),
    code("import numpy as np\n"
         "def board_to_array(s):\n"
         "    return np.array([0 if ch == '.' else (1 if ch == 'b' else -1) for ch in s]).reshape(15, 15)\n"
         "X = np.stack([board_to_array(s) for s in moves.board_after])\n"
         "print('Feature tensor:', X.shape, '| labels (move cell):', moves[['row', 'col']].shape)"),
    md("## Conclusion\n\n"
       "* **Uninformed vs informed search.** The Random agent never wins; adding domain knowledge "
       "(rules, then a heuristic evaluation) is what makes an agent play well.\n"
       "* **Alpha-beta pruning** gives the same decisions as minimax while exploring a fraction of the "
       "states; with move ordering the saving is even larger, which allows deeper search in the same time.\n"
       "* **Iterative deepening + transposition table** (Expert) searches deeper within its time budget "
       "(about 3x more states per move than fixed depth 3), but in this tournament it only tied with "
       "Alpha-Beta depth 3. Deeper search does not automatically mean stronger play: the heuristic's "
       "quality and the candidate cut-off limit what extra depth can find. This is a direction for future work.\n"
       "* The recorded games give a growing dataset for coaching and machine-learning extensions."),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "analysis/gomoku_analysis.ipynb")
print("wrote analysis/gomoku_analysis.ipynb")
