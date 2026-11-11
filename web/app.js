/* Intelligent Gomoku - browser front end.
 * Draws the board, handles clicks, menus, levels, sounds and animations.
 * Every AI decision is made in Python (web_app.py -> agents.py). */
"use strict";

const CELL = 40, PAD = 40;
const SVG_NS = "http://www.w3.org/2000/svg";

const OPPONENTS = {
  Easy:    { face: "🐣", name: "Pip the Chick", color: "#1baf7a", stars: 1, tech: "Random AI (uninformed)",
             blurb: "Just learning! Pip picks any empty spot at random." },
  Blind:   { face: "🦇", name: "Batty", color: "#52514e", stars: 1, tech: "Blind Minimax (uninformed search)",
             blurb: "Flies blind! Batty checks every square but only knows win or lose." },
  Medium:  { face: "🦊", name: "Foxy", color: "#2a78d6", stars: 2, tech: "Rule-Based AI (goal-based)",
             blurb: "Follows clever rules: win, block, then attack." },
  Minimax: { face: "🐢", name: "Turtle Max", color: "#eb6834", stars: 2, tech: "Minimax + heuristic (informed)",
             blurb: "Slow and steady: scores every board 2 moves ahead." },
  Hard:    { face: "🦉", name: "Professor Owl", color: "#6250d6", stars: 3, tech: "Minimax + Alpha-Beta pruning",
             blurb: "Thinks 3 moves ahead and skips useless branches." },
  Expert:  { face: "🐉", name: "Draco", color: "#e34948", stars: 4, tech: "Iterative deepening + memory",
             blurb: "Thinks as deep as it can for 2 seconds. Good luck!" },
};

const LEVELS = [
  { size: 9, op: "Easy", title: "First Steps",
    learn: "Pip is a <b>simple reflex agent</b> with <b>no search</b>: it picks randomly. That's an <b>uninformed</b> strategy." },
  { size: 9, op: "Blind", title: "Searching in the Dark",
    learn: "Batty uses <b>uninformed (blind) search</b>: it looks at every square, about 6,000 boards per move on 9×9, but only knows win or lose." },
  { size: 11, op: "Medium", title: "The Clever Fox",
    learn: "Foxy is a <b>goal-based agent</b>: fixed rules (win, block, attack) lead it towards five in a row." },
  { size: 11, op: "Minimax", title: "Slow and Steady",
    learn: "Turtle Max uses <b>Minimax with a heuristic function</b>: an <b>informed search</b> that gives every board a score." },
  { size: 13, op: "Medium", first: "ai", title: "Fox Goes First",
    learn: "In Gomoku, <b>moving first is an advantage</b>. Can you still win as White?" },
  { size: 13, op: "Hard", title: "The Wise Owl",
    learn: "<b>Alpha-beta pruning</b> gives the same answer as minimax but skips branches that cannot change the decision." },
  { size: 15, op: "Hard", title: "The Full Board",
    learn: "A bigger board means <b>more states</b>. <b>Candidate move generation</b> keeps the search small by looking only near the stones." },
  { size: 15, op: "Hard", first: "ai", title: "Owl Strikes First",
    learn: "Professor Owl is a <b>utility-based agent</b>: it picks the move with the highest heuristic utility." },
  { size: 15, op: "Expert", title: "Dragon's Den",
    learn: "Draco uses <b>iterative deepening</b> (search deeper and deeper until time runs out) and a <b>transposition table</b> (memory of boards it has seen)." },
  { size: 15, op: "Expert", first: "ai", title: "Boss Battle",
    learn: "You beat the strongest agent! You now know the whole path from <b>uninformed</b> to <b>informed</b> adversarial search. 🏆" },
];

const KID_REASONS = {
  "Completes five in a row": "Five in a row, I win! 🎉",
  "Blocks opponent's five": "Phew! I blocked your four just in time. 😅",
  "Creates an open four (unstoppable)": "Four in a row with both ends open. You can't stop both! 😎",
  "Creates a double threat (fork)": "A double attack: two threats at once! ⚡",
  "Blocks opponent's open three": "I saw your open three and blocked it. 👀",
  "Creates a double open three (fork)": "Two open threes at once, sneaky! 🦊",
  "Creates a four (forcing move)": "Four in a row! You have to block me now. 😏",
  "Prevents an opponent fork": "I stopped your double attack. 🛡️",
  "Creates an open three": "Three in a row with space on both sides. 👍",
  "Restricts opponent's development": "Getting in your way! 🚧",
  "Builds own shape": "Building my line, stone by stone. 🧱",
  "Positional / board control": "Taking a good spot near the middle. 📍",
  "Random legal move": "Eeny, meeny, miny, moe… here! 🎲",
  "Sees no win or loss within reach, so every move looks the same": "I can't see any win or loss nearby… every square looks the same to me! 🦇",
  "Ran out of search budget: the board is too big to search blindly": "Too many squares to check without clues! I'll just guess. 😵",
  "Rule 1: win immediately": "Five in a row, I win! 🎉",
  "Rule 2: block opponent's five": "Phew! I blocked your four. 😅",
  "Rule 3: create an open four": "Open four, you can't stop both ends! 😎",
  "Rule 4: create a four-three fork": "A double attack! ⚡",
  "Rule 4: create a double three": "Two open threes at once! 🦊",
  "Rule 5: block opponent's open three": "I blocked your open three. 👀",
  "Rule 5: stop opponent fork": "I stopped your double attack. 🛡️",
  "Rule 6: best attack + defence value": "This spot helps me and blocks you. 🎯",
};
const kid = (reason) => KID_REASONS[reason] || reason || "Hmm, this looks good.";

/* ------------------------------------------------------------------ utils */
const $ = (id) => document.getElementById(id);
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* storage unavailable */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* storage unavailable */ } },
};
const emptyBoard = (n) => Array.from({ length: n }, () => Array(n).fill(null));
const other = (c) => (c === "black" ? "white" : "black");
const cellName = (r, c) => String.fromCharCode(65 + c) + (r + 1);
const sleep = (ms) => new Promise((res) => setTimeout(res, ms));
const clock = (sec) => `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;

async function api(path, body) {
  const opts = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove("show"), 2600);
}

function confirmBox(title, text) {
  return new Promise((resolve) => {
    $("confirmTitle").textContent = title; $("confirmText").textContent = text; $("confirm").hidden = false;
    const done = (v) => { $("confirm").hidden = true; $("confirmYes").onclick = $("confirmNo").onclick = null; resolve(v); };
    $("confirmYes").onclick = () => done(true); $("confirmNo").onclick = () => done(false);
    $("confirmYes").focus();
  });
}

function winningLine(board, r, c) {
  const n = board.length, color = board[r][c];
  for (const [dr, dc] of [[0, 1], [1, 0], [1, 1], [1, -1]]) {
    const line = [[r, c]];
    for (const s of [1, -1]) {
      let rr = r + s * dr, cc = c + s * dc;
      while (rr >= 0 && rr < n && cc >= 0 && cc < n && board[rr][cc] === color) { line.push([rr, cc]); rr += s * dr; cc += s * dc; }
    }
    if (line.length >= 5) return line.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  }
  return null;
}
const isFull = (board) => board.every((row) => row.every((v) => v !== null));

/* ------------------------------------------------------------------ sound */
const Sound = {
  on: store.get("gomoku-sound", true),
  ctx: null,
  tone(freq, dur = 0.12, type = "sine", vol = 0.18, delay = 0) {
    if (!this.on) return;
    try {
      this.ctx = this.ctx || new (window.AudioContext || window.webkitAudioContext)();
      const t = this.ctx.currentTime + delay, o = this.ctx.createOscillator(), g = this.ctx.createGain();
      o.type = type; o.frequency.setValueAtTime(freq, t);
      g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
      o.connect(g).connect(this.ctx.destination); o.start(t); o.stop(t + dur + 0.02);
    } catch { /* audio unavailable */ }
  },
  place(color) { this.tone(color === "black" ? 420 : 560, 0.1, "triangle", 0.22); },
  hint() { [660, 880].forEach((f, i) => this.tone(f, 0.15, "sine", 0.15, i * 0.09)); },
  win() { [523, 659, 784, 1047].forEach((f, i) => this.tone(f, 0.22, "triangle", 0.2, i * 0.12)); },
  lose() { [440, 370, 311].forEach((f, i) => this.tone(f, 0.25, "sine", 0.16, i * 0.15)); },
  oops() { this.tone(200, 0.12, "square", 0.08); },
  click() { this.tone(700, 0.05, "sine", 0.1); },
};
function setSound(on) {
  Sound.on = on; store.set("gomoku-sound", on);
  $("soundBtn").textContent = on ? "🔊" : "🔇";
  $("pSoundBtn").textContent = on ? "🔊 Sound: on" : "🔇 Sound: off";
}

/* ------------------------------------------------------------------ confetti */
function confetti() {
  const cv = $("confetti"), ctx = cv.getContext("2d");
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  cv.width = innerWidth; cv.height = innerHeight;
  const colors = ["#2a78d6", "#eb6834", "#1baf7a", "#ffcf3d", "#e87ba4", "#6250d6"];
  const parts = Array.from({ length: 160 }, () => ({
    x: Math.random() * cv.width, y: -20 - Math.random() * cv.height * 0.5, vx: (Math.random() - 0.5) * 4,
    vy: 2 + Math.random() * 4, s: 6 + Math.random() * 8, a: Math.random() * 6, va: (Math.random() - 0.5) * 0.3,
    c: colors[Math.floor(Math.random() * colors.length)],
  }));
  const end = performance.now() + 3500;
  (function frame(now) {
    ctx.clearRect(0, 0, cv.width, cv.height);
    for (const p of parts) {
      p.x += p.vx; p.y += p.vy; p.vy += 0.04; p.a += p.va;
      ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.a); ctx.fillStyle = p.c;
      ctx.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); ctx.restore();
    }
    if (now < end) requestAnimationFrame(frame); else ctx.clearRect(0, 0, cv.width, cv.height);
  })(performance.now());
}

/* ------------------------------------------------------------------ board view */
class BoardView {
  constructor(svg, { onClick, numbers = false, size = 15, coords = true } = {}) {
    this.svg = svg; this.onClick = onClick; this.numbers = numbers; this.id = svg.id; this.coords = coords;
    this.setSize(size);
  }
  el(tag, attrs, parent) {
    const e = document.createElementNS(SVG_NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    (parent || this.svg).appendChild(e);
    return e;
  }
  xy(r, c) { return [PAD + c * CELL, PAD + r * CELL]; }
  setSize(n) { this.n = n; this.draw(); }
  draw() {
    const svg = this.svg, n = this.n, W = PAD * 2 + (n - 1) * CELL, id = this.id;
    svg.setAttribute("viewBox", `0 0 ${W} ${W}`);
    svg.innerHTML = "";
    const defs = this.el("defs", {});
    defs.innerHTML = `
      <linearGradient id="${id}-wood" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#f6d49c"/><stop offset=".5" stop-color="#ebb771"/><stop offset="1" stop-color="#dfa35c"/>
      </linearGradient>
      <radialGradient id="${id}-gBlack" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#777"/><stop offset=".55" stop-color="#1b1b1b"/><stop offset="1" stop-color="#000"/></radialGradient>
      <radialGradient id="${id}-gWhite" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#fff"/><stop offset=".7" stop-color="#e9e9e9"/><stop offset="1" stop-color="#c8c8c8"/></radialGradient>
      <filter id="${id}-shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="1.5" dy="2.5" stdDeviation="1.8" flood-opacity=".4"/></filter>`;
    this.el("rect", { x: 0, y: 0, width: W, height: W, rx: 26, fill: `url(#${id}-wood)` });
    for (let i = 0; i < Math.ceil(W / 72); i++) {
      this.el("path", { d: `M0 ${30 + i * 72} Q ${W / 2} ${10 + i * 72 + (i % 2) * 30} ${W} ${36 + i * 72}`, stroke: "#c98f4e", "stroke-width": 1.2, fill: "none", opacity: 0.35 });
    }
    const end = PAD + (n - 1) * CELL;
    for (let i = 0; i < n; i++) {
      const p = PAD + i * CELL;
      this.el("line", { x1: PAD, y1: p, x2: end, y2: p, class: "grid-line" });
      this.el("line", { x1: p, y1: PAD, x2: p, y2: end, class: "grid-line" });
      if (this.coords) {
        this.el("text", { x: p, y: 22, "text-anchor": "middle", class: "coord" }).textContent = String.fromCharCode(65 + i);
        this.el("text", { x: 18, y: p + 5, "text-anchor": "middle", class: "coord" }).textContent = i + 1;
      }
    }
    const m = Math.floor(n / 2), k = n >= 13 ? 3 : 2;
    const stars = n >= 9 ? [[k, k], [k, n - 1 - k], [m, m], [n - 1 - k, k], [n - 1 - k, n - 1 - k]] : [[m, m]];
    for (const [r, c] of stars) { const [x, y] = this.xy(r, c); this.el("circle", { cx: x, cy: y, r: 4.5, class: "star" }); }
    this.stones = this.el("g", {});
    this.overlay = this.el("g", {});
    this.ghost = this.el("circle", { r: 17, class: "ghost-stone", fill: `url(#${id}-gBlack)` });
    this.hit = this.el("rect", { x: 0, y: 0, width: W, height: W, fill: "transparent" });
    this.hit.addEventListener("click", (e) => { const rc = this.cellAt(e); if (rc && this.onClick) this.onClick(...rc); });
    this.hit.addEventListener("mousemove", (e) => this.hover(this.cellAt(e)));
    this.hit.addEventListener("mouseleave", () => this.ghost.classList.remove("show"));
  }
  cellAt(e) {
    const pt = this.svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(this.svg.getScreenCTM().inverse());
    const c = Math.round((p.x - PAD) / CELL), r = Math.round((p.y - PAD) / CELL);
    return r >= 0 && r < this.n && c >= 0 && c < this.n ? [r, c] : null;
  }
  hover(rc) {
    if (!rc || !this.canHover || !this.canHover(...rc)) { this.ghost.classList.remove("show"); return; }
    const [x, y] = this.xy(...rc);
    this.ghost.setAttribute("cx", x); this.ghost.setAttribute("cy", y);
    this.ghost.setAttribute("fill", `url(#${this.id}-${this.hoverColor === "white" ? "gWhite" : "gBlack"})`);
    this.ghost.classList.add("show");
  }
  clear() { this.stones.innerHTML = ""; this.overlay.innerHTML = ""; this.ghost.classList.remove("show"); }
  addStone(r, c, color, num, animate = true) {
    const [x, y] = this.xy(r, c);
    const g = this.el("g", { class: "stone" + (animate ? " drop" : ""), "data-rc": `${r},${c}` }, this.stones);
    this.el("circle", { cx: x, cy: y, r: 17, fill: `url(#${this.id}-${color === "black" ? "gBlack" : "gWhite"})`, filter: `url(#${this.id}-shadow)` }, g);
    if (this.numbers && num) {
      this.el("text", { x, y: y + 4, "text-anchor": "middle", class: "move-num", fill: color === "black" ? "#fff" : "#333" }, g).textContent = num;
    }
    this.markLast(r, c);
  }
  removeStone(r, c) { const s = this.stones.querySelector(`[data-rc="${r},${c}"]`); if (s) s.remove(); }
  markLast(r, c) {
    this.overlay.querySelectorAll(".last-mark, .last-ring").forEach((e) => e.remove());
    if (r === undefined) return;
    const [x, y] = this.xy(r, c);
    this.el("circle", { cx: x, cy: y, r: 21, class: "last-ring" }, this.overlay);
    if (!this.numbers) this.el("circle", { cx: x, cy: y, r: 4.5, class: "last-mark" }, this.overlay);
  }
  showWin(line) {
    const [x1, y1] = this.xy(...line[0]), [x2, y2] = this.xy(...line[line.length - 1]);
    for (const [r, c] of line) { const [x, y] = this.xy(r, c); this.el("circle", { cx: x, cy: y, r: 20, class: "win-ring" }, this.overlay); }
    this.el("line", { x1, y1, x2, y2, class: "win-line" }, this.overlay);
  }
  showHints(hints) {
    this.clearHints();
    hints.forEach((h, i) => {
      const [x, y] = this.xy(h.row, h.col);
      const g = this.el("g", { class: "hint" }, this.overlay);
      this.el("circle", { cx: x, cy: y, r: 16, class: "hint-ring" }, g);
      this.el("text", { x, y: y + 6, "text-anchor": "middle", class: "hint-num" }, g).textContent = i + 1;
    });
  }
  clearHints() { this.overlay.querySelectorAll(".hint").forEach((e) => e.remove()); }
}

/* ------------------------------------------------------------------ navigation */
let currentScreen = "home";
function go(name) {
  if (name === "friend") { startGame({ mode: "friend", size: 15 }); return; }
  if (currentScreen === "game" && name !== "game") Game.suspend();
  if (name !== "watch") Watch.pause();
  currentScreen = name;
  document.querySelectorAll(".screen").forEach((s) => s.classList.toggle("active", s.id === "screen-" + name));
  const navKey = name === "game" ? (Game.mode === "friend" ? "friend" : Game.levelIdx !== null ? "levels" : "pick") : name;
  document.querySelectorAll(".topnav [data-go]").forEach((b) => b.classList.toggle("current", b.dataset.go === navKey));
  $("modal").hidden = true; $("pauseMenu").hidden = true;
  if (name === "home") refreshContinue();
  if (name === "levels") renderLevels();
  if (name === "lab") Lab.open();
  scrollTo({ top: 0, behavior: "smooth" });
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-go]");
  if (!b) return;
  if (currentScreen === "game" && Game.inProgress() && b.dataset.go !== "game") {
    toast("Game saved. Press ▶️ Continue on the home screen to come back.");
  }
  go(b.dataset.go);
});

/* ------------------------------------------------------------------ main game */
const Game = {
  board: emptyBoard(15), size: 15, moves: [], turn: "black", mode: "ai", level: "Medium", human: "black",
  levelIdx: null, over: false, busy: false, paused: false, gen: 0, hints: 3, started: null, elapsed: 0,
  view: null,

  inProgress() { return this.moves.length > 0 && !this.over; },
  isHumanTurn() { return !this.over && !this.busy && !this.paused && (this.mode === "friend" || this.turn === this.human); },

  title() {
    if (this.mode === "friend") return `👫 Friend game · ${this.size}×${this.size}`;
    const op = OPPONENTS[this.level];
    if (this.levelIdx !== null) return `Level ${this.levelIdx + 1}: ${LEVELS[this.levelIdx].title} · ${this.size}×${this.size}`;
    return `${op.face} vs ${op.name} · ${this.size}×${this.size}`;
  },

  setup(cfg) {
    this.gen++;
    Object.assign(this, { mode: cfg.mode, size: cfg.size || 15, levelIdx: cfg.levelIdx ?? null });
    if (cfg.level) this.level = cfg.level;
    this.human = cfg.mode === "ai" && cfg.first === "ai" ? "white" : "black";
    this.board = emptyBoard(this.size); this.moves = []; this.turn = "black";
    this.over = false; this.busy = false; this.paused = false; this.hints = cfg.hints ?? 3;
    this.started = new Date().toISOString(); this.elapsed = cfg.elapsed || 0;
    if (this.view.n !== this.size) this.view.setSize(this.size); else this.view.clear();
    $("hintCount").textContent = this.hints; $("gameTitle").textContent = this.title();
    $("pausedCover").hidden = true;
    this.setupPlayers(); this.resetBrain(); this.tick(true);
  },

  begin() {
    this.updateTurn();
    if (this.mode === "ai" && this.turn !== this.human) this.aiMove();
  },

  restart() { this.setup({ mode: this.mode, size: this.size, level: this.level, levelIdx: this.levelIdx, first: this.human === "white" ? "ai" : "human" }); this.save(); this.begin(); },

  setupPlayers() {
    const op = OPPONENTS[this.level];
    const you = { face: "🙂", name: "You" }, friend1 = { face: "😀", name: "Player 1" }, friend2 = { face: "😎", name: "Player 2" };
    let black, white;
    if (this.mode === "friend") { black = friend1; white = friend2; }
    else if (this.human === "black") { black = you; white = op; } else { black = op; white = you; }
    $("avBlack").textContent = black.face; $("nameBlack").textContent = black.name;
    $("avWhite").textContent = white.face; $("nameWhite").textContent = white.name;
    $("brainPanel").style.display = this.mode === "friend" ? "none" : "";
    $("bubbleFace").textContent = op.face;
  },

  resetBrain() {
    const op = OPPONENTS[this.level], info = Lab.agents && Lab.agents[this.level];
    this.say(this.mode === "ai" ? `Hi, I'm ${op.name}! ${op.blurb}` : "");
    $("bsBoards").textContent = "–"; $("bsDepth").textContent = "–"; $("bsTime").textContent = "–";
    $("bsTech").textContent = `Algorithm: ${op.tech}`;
    $("agentTags").innerHTML = info
      ? `<span class="tag">🧩 ${info.agent_type}</span><span class="tag ${info.search.startsWith("Uninformed") ? "tag-un" : "tag-in"}">🔎 ${info.search}</span>`
      : "";
  },

  say(text, thinking = false) {
    $("bubbleText").innerHTML = thinking ? `Hmm, let me think<span class="dots"></span>` : text;
    $("brainPanel").classList.toggle("thinking", thinking);
  },

  updateTurn() {
    $("pcBlack").classList.toggle("turn", !this.over && this.turn === "black");
    $("pcWhite").classList.toggle("turn", !this.over && this.turn === "white");
    let text;
    if (this.over) text = "Game over";
    else if (this.paused) text = "Paused ⏸";
    else if (this.mode === "friend") text = `${this.turn === "black" ? "Player 1 (Black)" : "Player 2 (White)"}'s turn`;
    else text = this.turn === this.human ? "Your turn! 👆" : `${OPPONENTS[this.level].name} is thinking…`;
    $("turnBanner").textContent = text;
    $("moveCount").textContent = `Move ${this.moves.length}`;
    $("undoBtn").disabled = this.busy || this.paused || this.moves.length === 0;
    $("hintBtn").disabled = !this.isHumanTurn() || this.hints <= 0;
    $("newBtn").disabled = this.paused;
    $("pauseBtn").disabled = this.over;
    this.view.hoverColor = this.turn;
  },

  /* ---- timer ---- */
  tick(resetOnly = false) {
    clearInterval(this.timerId);
    $("timer").textContent = "⏱ " + clock(this.elapsed);
    if (resetOnly && this.elapsed === 0) { /* fall through to start */ }
    this.timerId = setInterval(() => {
      if (this.paused || this.over || currentScreen !== "game" || !this.moves.length) return;
      this.elapsed++; $("timer").textContent = "⏱ " + clock(this.elapsed);
      if (this.elapsed % 5 === 0) this.save();
    }, 1000);
  },

  /* ---- pause / resume / exit ---- */
  pause() {
    if (this.over || this.paused) return;
    this.paused = true; this.save();
    $("pausedCover").hidden = false;
    $("pauseInfo").textContent = `${this.title()} · move ${this.moves.length} · ⏱ ${clock(this.elapsed)}`;
    $("pauseMenu").hidden = false; $("resumeBtn").focus();
    this.updateTurn();
  },
  resume() {
    if (!this.paused) return;
    this.paused = false; $("pauseMenu").hidden = true; $("pausedCover").hidden = true;
    this.updateTurn();
  },
  suspend() {
    // leaving the game screen: freeze silently, the game stays saved
    if (!this.over) { this.paused = true; this.save(); }
    $("pauseMenu").hidden = true;
  },
  async exit() {
    $("pauseMenu").hidden = true;
    if (this.inProgress()) {
      const ok = await confirmBox("Exit this game?", "Don't worry, your game is saved. Press ▶️ Continue on the home screen to come back to it.");
      if (!ok) { if (this.paused) $("pauseMenu").hidden = false; return; }
    }
    go(this.levelIdx !== null ? "levels" : "home");
  },

  /* ---- save / continue ---- */
  save() {
    if (!this.inProgress()) return;
    store.set("gomoku-save", {
      mode: this.mode, size: this.size, level: this.level, levelIdx: this.levelIdx, human: this.human,
      moves: this.moves, hints: this.hints, elapsed: this.elapsed, savedAt: Date.now(),
    });
  },
  clearSave() { store.del("gomoku-save"); },
  restore(s) {
    this.setup({ mode: s.mode, size: s.size, level: s.level, levelIdx: s.levelIdx, first: s.human === "white" ? "ai" : "human", hints: s.hints, elapsed: s.elapsed });
    for (const m of s.moves) {
      this.board[m.row][m.col] = m.player; this.moves.push(m); this.view.addStone(m.row, m.col, m.player, 0, false);
    }
    this.turn = this.moves.length % 2 === 0 ? "black" : "white";
    this.say("Welcome back! Let's continue. 👋");
    go("game");
    this.begin();
  },

  /* ---- moves ---- */
  click(r, c) {
    if (this.paused) { toast("The game is paused. Press ▶️ Resume."); return; }
    if (!this.isHumanTurn()) { if (this.busy) toast("Wait, the computer is thinking! 🤔"); return; }
    if (this.board[r][c]) { Sound.oops(); return; }
    this.place(r, c, this.turn);
  },

  place(r, c, color, meta = {}) {
    this.board[r][c] = color;
    this.moves.push({ player: color, row: r, col: c, elapsed_ms: this.elapsed * 1000, ...meta });
    this.view.clearHints();
    this.view.addStone(r, c, color);
    Sound.place(color);
    const line = winningLine(this.board, r, c);
    if (line) { this.view.showWin(line); return this.finish(color); }
    if (isFull(this.board)) return this.finish("draw");
    this.turn = other(color);
    this.save();
    this.updateTurn();
    if (this.mode === "ai" && this.turn !== this.human) this.aiMove();
  },

  async aiMove() {
    const gen = this.gen;
    this.busy = true; this.updateTurn(); this.say("", true);
    const started = performance.now();
    try {
      const res = await api("/api/ai-move", { board: this.board, color: this.turn, level: this.level });
      await sleep(Math.max(0, 450 - (performance.now() - started)));  // let kids see the "thinking"
      while (this.paused && gen === this.gen) await sleep(150);       // hold the move while paused
      if (gen !== this.gen || this.over) return;
      this.busy = false;
      const s = res.stats;
      this.say(kid(s.reason));
      $("bsBoards").textContent = s.nodes.toLocaleString();
      $("bsDepth").textContent = s.depth || "1";
      $("bsTime").textContent = s.time_ms < 1000 ? `${Math.round(s.time_ms)} ms` : `${(s.time_ms / 1000).toFixed(1)} s`;
      $("bsTech").textContent = `${s.agent}: ${s.nodes.toLocaleString()} states, depth ${s.depth}, ${s.cutoffs.toLocaleString()} prunes` +
        (s.tt_hits ? `, ${s.tt_hits.toLocaleString()} memory hits` : "") + `. Reason: ${s.reason}`;
      if (res.move) {
        this.place(res.move[0], res.move[1], this.turn,
          { ai_engine: s.agent, ai_nodes: s.nodes, ai_depth: s.depth, ai_time_ms: Math.round(s.time_ms), ai_reason: s.reason });
      } else this.finish("draw");
    } catch (err) {
      if (gen !== this.gen) return;
      this.busy = false; this.updateTurn();
      this.say("Oops, I couldn't reach my brain (the Python server). Is web_app.py running?");
      console.error(err);
    }
  },

  async hint() {
    if (!this.isHumanTurn() || this.hints <= 0) return;
    try {
      const { hints } = await api("/api/hint", { board: this.board, color: this.turn });
      this.hints--; $("hintCount").textContent = this.hints; this.updateTurn(); this.save();
      this.view.showHints(hints);
      Sound.hint();
      this.say(`💡 Try one of these:<br>${hints.map((h, i) => `<b>${i + 1}.</b> ${cellName(h.row, h.col)}: ${h.reason}`).join("<br>")}`);
    } catch (err) { toast("Couldn't get a hint 😕"); console.error(err); }
  },

  undo() {
    if (this.busy || this.paused || !this.moves.length) return;
    this.gen++;
    let n = 1;
    if (this.mode === "ai" && this.moves.length > 1 && this.moves[this.moves.length - 1].player !== this.human) n = 2;
    for (let i = 0; i < n; i++) {
      const m = this.moves.pop(); this.board[m.row][m.col] = null; this.view.removeStone(m.row, m.col);
    }
    this.over = false; this.busy = false;
    this.view.overlay.innerHTML = "";
    const last = this.moves[this.moves.length - 1];
    if (last) this.view.markLast(last.row, last.col);
    this.turn = this.moves.length % 2 === 0 ? "black" : "white";
    if (this.moves.length) this.save(); else this.clearSave();
    this.updateTurn();
    if (this.mode === "ai" && this.turn !== this.human) this.aiMove();
  },

  async finish(winner) {
    this.over = true; this.busy = false; this.updateTurn(); this.clearSave();
    const humanWon = this.mode === "friend" ? winner !== "draw" : winner === this.human;
    const op = OPPONENTS[this.level];
    let face, title, sub;
    if (winner === "draw") { face = "🤝"; title = "It's a draw!"; sub = "The whole board is full. Great defending!"; }
    else if (this.mode === "friend") { face = "🏆"; title = `${winner === "black" ? "Player 1" : "Player 2"} wins!`; sub = "Five in a row!"; }
    else if (humanWon) { face = "🎉"; title = this.levelIdx !== null ? `Level ${this.levelIdx + 1} complete!` : "You won!"; sub = `You beat ${op.name}! ${op.face}`; }
    else { face = op.face; title = `${op.name} wins this time`; sub = "Don't give up. Check the tips below and try again!"; }
    if (humanWon) { Sound.win(); confetti(); } else if (winner !== "draw") Sound.lose();
    if (this.mode === "ai") this.say(humanWon ? "Wow, you got me! 😲 Play again?" : winner === "draw" ? "A draw! Good game." : "Good game! 😊");

    $("modalFace").textContent = face; $("modalTitle").textContent = title; $("modalSub").textContent = sub;
    $("modalStars").innerHTML = ""; $("modalReport").innerHTML = "<p>Looking at your game…</p>";
    const isLevel = this.levelIdx !== null, nextIdx = isLevel ? this.levelIdx + 1 : null;
    $("nextLevelBtn").hidden = !(isLevel && humanWon && nextIdx < LEVELS.length);
    $("againBtn").textContent = isLevel && !humanWon ? "Try again" : "Play again";
    $("modalLearned").hidden = !isLevel;
    if (isLevel) $("modalLearned").innerHTML = `🎓 <b>AI idea in this level:</b> ${LEVELS[this.levelIdx].learn}`;
    await sleep(900);
    if (currentScreen === "game") $("modal").hidden = false;

    const black = this.mode === "friend" ? "Player 1" : this.human === "black" ? "Human" : op.name;
    const white = this.mode === "friend" ? "Player 2" : this.human === "white" ? "Human" : op.name;
    const modeName = this.mode === "friend" ? "friend" : isLevel ? `level${this.levelIdx + 1}` : `ai_${this.level}`;
    api("/api/save", { mode: modeName, winner, moves: this.moves, size: this.size, started_at: this.started, black, white })
      .catch((e) => console.error(e));

    const perspective = this.mode === "friend" ? (winner === "white" ? "white" : "black") : this.human;
    try {
      const a = await api("/api/analyze", { moves: this.moves, perspective, size: this.size });
      this.renderReport(a, this.mode === "friend" ? (perspective === "black" ? "Player 1" : "Player 2") : "you");
      if (isLevel && humanWon) Progress.complete(this.levelIdx, a.stars);
    } catch (err) {
      $("modalReport").innerHTML = "<p>Game analysis is not available right now.</p>"; console.error(err);
      if (isLevel && humanWon) Progress.complete(this.levelIdx, 1);
    }
  },

  renderReport(a, who) {
    $("modalStars").innerHTML = [1, 2, 3].map((i) => `<span class="${i <= a.stars ? "" : "off"}">⭐</span>`).join("");
    const label = { missed_win: "🎯 Missed win", missed_block: "🧱 Missed block", missed_defence: "👀 Missed open three",
                    weak_move: "🤔 Could be better", strong_move: "💪 Great move", danger: "⚠️ Watch out" };
    const pick = (types) => a.events.filter((e) => types.includes(e.type)).slice(0, 4)
      .map((e) => `<li><b>Move ${e.move_no} (${e.cell})</b>: ${label[e.type]}. ${e.text}</li>`).join("");
    const good = pick(["strong_move"]), bad = pick(["missed_win", "missed_block", "missed_defence", "weak_move"]);
    $("modalReport").innerHTML = `
      <h4>📊 How ${who} played</h4>
      <p>${a.your_moves} moves · ${a.strong_moves} great moves · ${a.total_mistakes} mistakes · ${a.dangers} danger moments</p>
      ${good ? `<h4>💪 Great moves</h4><ul>${good}</ul>` : ""}
      ${bad ? `<h4>📝 Things to practise</h4><ul>${bad}</ul>` : ""}
      <div class="tip">💡 <b>Tip:</b> ${a.tip}</div>`;
  },
};

function startGame(cfg) {
  Game.setup(cfg);
  go("game");
  Game.begin();
}

/* ------------------------------------------------------------------ continue */
function refreshContinue() {
  const s = store.get("gomoku-save", null);
  $("continueBtn").hidden = !s; $("continueInfo").hidden = !s;
  if (s) {
    const who = s.mode === "friend" ? "Friend game" : s.levelIdx !== null && s.levelIdx !== undefined
      ? `Level ${s.levelIdx + 1}: ${LEVELS[s.levelIdx].title}` : `vs ${OPPONENTS[s.level].face} ${OPPONENTS[s.level].name}`;
    $("continueInfo").textContent = `Saved: ${who}, ${s.size}×${s.size}, move ${s.moves.length}, ${clock(s.elapsed || 0)} played`;
  }
}
$("continueBtn").onclick = () => { const s = store.get("gomoku-save", null); if (s) Game.restore(s); };

/* ------------------------------------------------------------------ levels */
const Progress = {
  data: store.get("gomoku-progress", { unlocked: 1, stars: {} }),
  complete(idx, stars) {
    const prev = this.data.stars[idx] || 0;
    this.data.stars[idx] = Math.max(prev, stars);
    this.data.unlocked = Math.max(this.data.unlocked, Math.min(LEVELS.length, idx + 2));
    store.set("gomoku-progress", this.data);
    if (!prev) toast(idx + 1 < LEVELS.length ? `🔓 Level ${idx + 2} unlocked!` : "🏆 You finished every level!");
  },
  reset() { this.data = { unlocked: 1, stars: {} }; store.set("gomoku-progress", this.data); },
};
function renderLevels() {
  const d = Progress.data, done = Object.keys(d.stars).length;
  const starTotal = Object.values(d.stars).reduce((a, b) => a + b, 0);
  $("progressFill").style.width = `${(done / LEVELS.length) * 100}%`;
  $("progressText").textContent = `${done} / ${LEVELS.length} levels · ${starTotal} / ${LEVELS.length * 3} ⭐`;
  $("levelGrid").innerHTML = LEVELS.map((L, i) => {
    const op = OPPONENTS[L.op], locked = i + 1 > d.unlocked, stars = d.stars[i] || 0;
    return `<button class="level ${locked ? "locked" : ""} ${stars ? "done" : ""}" data-level-idx="${i}" ${locked ? "aria-disabled=\"true\"" : ""}>
      <span class="lv-num">${locked ? "🔒" : i + 1}</span>
      <span class="lv-face">${op.face}</span>
      <b>${L.title}</b>
      <small>${L.size}×${L.size} · vs ${op.name}${L.first === "ai" ? " · they start" : ""}</small>
      <span class="lv-stars">${[1, 2, 3].map((s) => `<i class="${s <= stars ? "" : "off"}">⭐</i>`).join("")}</span>
    </button>`;
  }).join("");
}
$("levelGrid").addEventListener("click", (e) => {
  const b = e.target.closest("[data-level-idx]");
  if (!b) return;
  const i = +b.dataset.levelIdx;
  if (i + 1 > Progress.data.unlocked) { Sound.oops(); toast(`Beat level ${i} first to unlock this one! 🔒`); return; }
  playLevel(i);
});
function playLevel(i) {
  const L = LEVELS[i];
  startGame({ mode: "ai", size: L.size, level: L.op, levelIdx: i, first: L.first || "human" });
  toast(`Level ${i + 1}: ${L.title}`);
}
$("resetProgress").onclick = async () => {
  if (await confirmBox("Reset progress?", "This locks all levels again and clears your stars.")) { Progress.reset(); renderLevels(); }
};

/* ------------------------------------------------------------------ quick play */
let firstMove = "human", pickSize = 15;
function buildPicker() {
  const wrap = $("opponentCards");
  wrap.innerHTML = Object.entries(OPPONENTS).map(([lvl, o]) => `
    <div class="op-card">
      <span class="op-face">${o.face}</span>
      <h3>${o.name}</h3>
      <span class="op-level" style="background:${o.color}">${lvl === "Blind" ? "Blind search" : lvl === "Minimax" ? "Minimax" : lvl}</span>
      <div class="op-meter" aria-label="Difficulty ${o.stars} of 4">${[1, 2, 3, 4].map((i) => `<i class="${i <= o.stars ? "on" : ""}"></i>`).join("")}</div>
      <p>${o.blurb}</p>
      <div class="op-tech">🧠 ${o.tech}</div>
      <button class="big-btn primary" data-level="${lvl}">Play ${o.name.split(" ")[0]}</button>
    </div>`).join("");
  wrap.addEventListener("click", (e) => {
    const b = e.target.closest("[data-level]");
    if (b) startGame({ mode: "ai", size: pickSize, level: b.dataset.level, first: firstMove });
  });
  const seg = (attr, set) => document.querySelectorAll(`[data-${attr}]`).forEach((b) => b.addEventListener("click", () => {
    set(b.dataset[attr]);
    document.querySelectorAll(`[data-${attr}]`).forEach((x) => { x.classList.toggle("active", x === b); x.setAttribute("aria-checked", x === b); });
  }));
  seg("first", (v) => { firstMove = v; });
  seg("size", (v) => { pickSize = +v; });
}

/* ------------------------------------------------------------------ AI vs AI */
const Watch = {
  /* Robot Battle. Robot 1 and Robot 2 swap colours every game, and each random
     opening is played twice (once with each robot as Black), so the scoreboard
     compares the robots fairly; Black's first-move advantage is counted apart. */
  view: null, board: emptyBoard(15), moves: [], running: false, gen: 0, gamesLeft: 0, gameNo: 0,
  stats: {}, colors: { A: "black", B: "white" }, opening: [],
  score: store.get("gomoku-score2", { A: 0, B: 0, draw: 0, black: 0, white: 0 }),

  init() {
    const opts = Object.entries(OPPONENTS).map(([lvl, o]) => `<option value="${lvl}">${o.face} ${o.name} (${o.tech})</option>`).join("");
    $("watchA").innerHTML = opts; $("watchB").innerHTML = opts;
    $("watchA").value = "Medium"; $("watchB").value = "Hard";
    $("watchStart").onclick = () => this.start();
    $("watchPause").onclick = () => this.pause();
    $("watchReset").onclick = () => this.reset();
    $("watchSize").onchange = () => this.reset();
    $("watchA").onchange = $("watchB").onchange = () => { this.clearScore(); this.renderStats(); };
    $("scoreReset").onclick = () => this.clearScore();
    this.renderScore(); this.renderStats();
  },
  size() { return +$("watchSize").value; },
  robot(id) { return OPPONENTS[$(id === "A" ? "watchA" : "watchB").value]; },
  level(id) { return $(id === "A" ? "watchA" : "watchB").value; },
  idOf(color) { return this.colors.A === color ? "A" : "B"; },

  clearScore() { this.score = { A: 0, B: 0, draw: 0, black: 0, white: 0 }; store.set("gomoku-score2", this.score); this.renderScore(); },
  renderScore() {
    const s = this.score, a = this.robot("A"), b = this.robot("B");
    $("scA").textContent = s.A; $("scB").textContent = s.B; $("scDraw").textContent = s.draw;
    $("scAFace").textContent = a.face; $("scBFace").textContent = b.face;
    $("scAName").textContent = `${a.name} wins`; $("scBName").textContent = `${b.name} wins`;
    $("scBlack").textContent = s.black; $("scWhite").textContent = s.white;
    const decided = s.black + s.white;
    $("colourNote").textContent = decided
      ? `Black won ${Math.round((100 * s.black) / decided)}% of decided games. Gomoku is known to favour the first player, which is why the robots swap colours.`
      : "";
  },
  renderStats() {
    $("watchStats").innerHTML = ["A", "B"].map((id) => {
      const o = this.robot(id), s = this.stats[id], color = this.colors[id];
      const body = s && s.moves
        ? `${s.moves} moves · ${Math.round(s.nodes / s.moves).toLocaleString()} boards/move · ${Math.round(s.ms / s.moves).toLocaleString()} ms/move<br><i>${kid(s.last)}</i>`
        : o.blurb;
      return `<div class="rs"><b>${color === "black" ? "⚫" : "⚪"} ${o.face} ${o.name}</b> <small>(${color} this game)</small><br>${body}</div>`;
    }).join("");
  },
  reset() {
    this.gen++; this.running = false; this.board = emptyBoard(this.size()); this.moves = []; this.stats = {};
    this.gamesLeft = 0; this.gameNo = 0; this.colors = { A: "black", B: "white" }; this.opening = [];
    this.view.setSize(this.size()); $("watchStatus").textContent = "Pick two robots and press Start"; this.renderStats();
  },
  pause() { if (this.running) { this.running = false; $("watchStatus").textContent = "Paused ⏸ (press Start to resume)"; } },
  async start() {
    if (this.running) return;
    if (!this.gamesLeft) { this.gamesLeft = parseInt($("watchGames").value, 10); this.gameNo = 0; await this.newGame(); }
    this.running = true;
    this.loop(this.gen);
  },
  async newGame() {
    this.gen++; this.gameNo++;
    this.board = emptyBoard(this.size()); this.moves = []; this.stats = {};
    const swap = $("watchSwap").checked, secondOfPair = this.gameNo % 2 === 0;
    this.colors = swap && secondOfPair ? { A: "white", B: "black" } : { A: "black", B: "white" };
    const stones = +$("watchOpening").value;
    // a new random opening for every pair of games; the second game of a pair reuses it with colours swapped
    if (!swap || !secondOfPair || this.opening.length !== stones) {
      this.opening = [];
      if (stones) {
        try { this.opening = (await api(`/api/opening?stones=${stones}&size=${this.size()}`)).moves; }
        catch (err) { console.error(err); }
      }
    }
    this.view.setSize(this.size());
    for (const m of this.opening) { this.board[m.row][m.col] = m.player; this.moves.push({ ...m }); this.view.addStone(m.row, m.col, m.player, this.moves.length, false); }
    this.view.markLast();
    this.renderStats();
  },
  async loop(gen) {
    while (this.running && gen === this.gen) {
      const color = this.moves.length % 2 === 0 ? "black" : "white", id = this.idOf(color), robot = this.robot(id);
      $("watchStatus").textContent = `Game ${this.gameNo}: ${robot.face} ${robot.name} (${color}) is thinking… · ${this.gamesLeft} game(s) left`;
      let res;
      try { res = await api("/api/ai-move", { board: this.board, color, level: this.level(id) }); }
      catch (err) { $("watchStatus").textContent = "Can't reach the Python server. Is web_app.py running?"; this.running = false; return; }
      while (!this.running && gen === this.gen) await sleep(150);  // paused mid-think: hold the move
      if (gen !== this.gen) return;
      const s = res.stats, st = this.stats[id] || (this.stats[id] = { moves: 0, nodes: 0, ms: 0, last: "" });
      st.moves++; st.nodes += s.nodes; st.ms += s.time_ms; st.last = s.reason;
      if (!res.move) return this.endGame("draw", gen);
      const [r, c] = res.move;
      this.board[r][c] = color; this.moves.push({ player: color, row: r, col: c, ai_engine: s.agent, ai_nodes: s.nodes, ai_depth: s.depth, ai_time_ms: Math.round(s.time_ms), ai_reason: s.reason });
      this.view.addStone(r, c, color, this.moves.length); Sound.place(color); this.renderStats();
      const line = winningLine(this.board, r, c);
      if (line) { this.view.showWin(line); return this.endGame(color, gen); }
      if (isFull(this.board)) return this.endGame("draw", gen);
      await sleep(+$("watchSpeed").max - +$("watchSpeed").value);
    }
  },
  async endGame(winner, gen) {
    if (winner === "draw") this.score.draw++;
    else { this.score[winner]++; this.score[this.idOf(winner)]++; }
    store.set("gomoku-score2", this.score); this.renderScore();
    const who = winner === "draw" ? null : this.robot(this.idOf(winner));
    $("watchStatus").textContent = winner === "draw" ? `Game ${this.gameNo}: draw!` : `🏆 Game ${this.gameNo}: ${who.face} ${who.name} (${winner}) wins in ${this.moves.length} moves!`;
    const black = this.robot(this.idOf("black")).name, white = this.robot(this.idOf("white")).name;
    api("/api/save", { mode: "watch", winner, moves: this.moves, size: this.size(), black, white }).catch(() => {});
    this.gamesLeft--;
    if (this.gamesLeft > 0 && this.running && gen === this.gen) {
      await sleep(1500);
      if (!this.running || gen !== this.gen) return;
      await this.newGame();
      this.loop(this.gen);
    } else this.running = false;
  },
};

/* ------------------------------------------------------------------ AI Lab */
const Lab = {
  agents: null, heurView: null, heurBoard: emptyBoard(9), heurColor: "black",

  async loadAgents() {
    if (this.agents) return this.agents;
    try { this.agents = await api("/api/agents"); } catch (err) { console.error(err); }
    return this.agents;
  },
  async open() {
    const a = await this.loadAgents();
    if (!a) return;
    $("agentTable").innerHTML = `<tr><th>Robot</th><th>Algorithm</th><th>Agent type</th><th>Search</th><th>Knowledge used</th></tr>` +
      Object.entries(a).map(([lvl, info]) => {
        const o = OPPONENTS[lvl];
        return `<tr><td>${o.face} ${o.name}</td><td>${info.algorithm}</td><td>${info.agent_type}</td>
          <td><span class="tag ${info.search.startsWith("Uninformed") ? "tag-un" : "tag-in"}">${info.search}</span></td><td>${info.knowledge}</td></tr>`;
      }).join("");
  },
  sampleBoard(n) {
    const b = emptyBoard(n), c = Math.floor(n / 2);
    b[c][c] = "black"; b[c][c + 1] = "white"; b[c + 1][c] = "black";
    return b;
  },
  async compare() {
    const n = +$("cmpSize").value;
    $("cmpRun").disabled = true; $("cmpOut").innerHTML = "<p>Running the searches… 🔎</p>";
    try {
      const d = await api("/api/compare", { board: this.sampleBoard(n), color: "white" });
      const max = Math.max(...d.results.map((r) => r.nodes));
      $("cmpOut").innerHTML = `<p class="small">${n}×${n} board: <b>${d.empty_cells}</b> empty cells, but only <b>${d.candidate_cells}</b> candidate cells near the stones.</p>` +
        d.results.map((r) => `
          <div class="bar-row">
            <div class="bar-label"><b>${r.algorithm}</b> <span class="tag ${r.kind === "Uninformed" ? "tag-un" : "tag-in"}">${r.kind}</span></div>
            <div class="bar-track"><div class="bar-fill ${r.kind === "Uninformed" ? "un" : "in"}" style="width:${Math.max(1.5, (Math.log10(r.nodes + 1) / Math.log10(max + 1)) * 100)}%"></div></div>
            <div class="bar-val">${r.nodes.toLocaleString()} states · ${r.time_ms} ms</div>
          </div>`).join("") +
        `<p class="small">Bar length uses a log scale. Same position, same depth: the informed searches look at far fewer boards and still find a sensible move.</p>`;
    } catch (err) { $("cmpOut").innerHTML = "<p>Couldn't run the experiment. Is web_app.py running?</p>"; }
    $("cmpRun").disabled = false;
  },
  async space() {
    $("spaceRun").disabled = true;
    const t = $("spaceTable");
    t.querySelectorAll("tr:not(:first-child)").forEach((r) => r.remove());
    for (const n of [7, 9, 11, 13, 15]) {
      const row = t.insertRow(); row.innerHTML = `<td>${n}×${n}</td><td>${n * n}</td><td>≈ 10<sup>${Math.round(n * n * Math.log10(3))}</sup></td><td>…</td><td>…</td>`;
      try {
        const d = await api("/api/compare", { board: this.sampleBoard(n), color: "white" });
        const get = (name) => d.results.find((r) => r.algorithm === name).nodes.toLocaleString();
        row.cells[3].textContent = get("Blind Minimax"); row.cells[4].textContent = get("Alpha-Beta");
      } catch { row.cells[3].textContent = row.cells[4].textContent = "error"; }
    }
    $("spaceRun").disabled = false;
  },
  heurClick(r, c) {
    const b = this.heurBoard;
    b[r][c] = this.heurColor === "erase" ? null : (b[r][c] === this.heurColor ? null : this.heurColor);
    this.heurRender();
  },
  heurRender() {
    const b = this.heurBoard;
    this.heurView.clear();
    b.forEach((row, rr) => row.forEach((v, cc) => { if (v) this.heurView.addStone(rr, cc, v, 0, false); }));
    this.heurView.markLast();
    this.heurEval();
  },
  async heurEval() {
    try {
      const d = await api("/api/evaluate", { board: this.heurBoard });
      const capped = Math.max(-1, Math.min(1, Math.sign(d.score) * Math.log10(Math.abs(d.score) + 1) / 7));
      $("heurMeter").style.width = `${50 + capped * 50}%`;
      $("heurVerdict").innerHTML = d.score === 0 ? "Score 0: even position" :
        `Score <b>${d.score.toLocaleString()}</b>: ${d.score > 0 ? "⚫ Black" : "⚪ White"} is ahead${Math.abs(d.score) >= d.win_score ? " (five in a row!)" : ""}`;
      const rows = d.patterns.black.map((p, i) => {
        const w = d.patterns.white[i];
        return `<tr><td>${p.name}</td><td>${p.weight.toLocaleString()}</td><td>${p.count}</td><td>${w.count}</td></tr>`;
      }).join("");
      $("heurTable").innerHTML = `<table class="lab-table"><tr><th>Pattern</th><th>Weight</th><th>⚫ count</th><th>⚪ count</th></tr>${rows}
        <tr><th>Total points</th><td></td><th>${d.black_points.toLocaleString()}</th><th>${d.white_points.toLocaleString()}</th></tr></table>`;
    } catch (err) { $("heurVerdict").textContent = "Couldn't reach the Python server."; }
  },
  init() {
    document.querySelectorAll(".lab-tab").forEach((t) => t.addEventListener("click", () => {
      document.querySelectorAll(".lab-tab").forEach((x) => x.classList.toggle("active", x === t));
      document.querySelectorAll(".lab-panel").forEach((p) => p.classList.toggle("active", p.id === "lab-" + t.dataset.lab));
    }));
    $("cmpRun").onclick = () => this.compare();
    $("spaceRun").onclick = () => this.space();
    this.heurView = new BoardView($("heurBoard"), { size: 9, coords: false, onClick: (r, c) => this.heurClick(r, c) });
    this.heurView.canHover = (r, c) => !this.heurBoard[r][c] && this.heurColor !== "erase";
    document.querySelectorAll("[data-heur]").forEach((b) => b.addEventListener("click", () => {
      this.heurColor = b.dataset.heur; this.heurView.hoverColor = this.heurColor;
      document.querySelectorAll("[data-heur]").forEach((x) => x.classList.toggle("active", x === b));
    }));
    $("heurClear").onclick = () => { this.heurBoard = emptyBoard(9); this.heurView.clear(); this.heurEval(); };
    // a small example position to start with
    [[4, 3, "black"], [4, 4, "black"], [4, 5, "black"], [3, 4, "white"], [5, 5, "white"]].forEach(([r, c, v]) => { this.heurBoard[r][c] = v; });
    this.heurRender();
  },
};

/* ------------------------------------------------------------------ learn page + hero */
function miniBoard(stones, size = 7, ring = []) {
  const s = 24, p = 14, w = p * 2 + (size - 1) * s;
  let out = `<svg viewBox="0 0 ${w} ${w}"><rect width="${w}" height="${w}" rx="12" fill="#ebb771"/>`;
  for (let i = 0; i < size; i++) {
    out += `<line x1="${p}" y1="${p + i * s}" x2="${p + (size - 1) * s}" y2="${p + i * s}" stroke="#8b5a2b" stroke-width="1.2" opacity=".7"/>`;
    out += `<line x1="${p + i * s}" y1="${p}" x2="${p + i * s}" y2="${p + (size - 1) * s}" stroke="#8b5a2b" stroke-width="1.2" opacity=".7"/>`;
  }
  for (const [r, c, col] of stones) {
    out += `<circle cx="${p + c * s}" cy="${p + r * s}" r="10" fill="${col === "b" ? "#1b1b1b" : "#f4f4f4"}" stroke="${col === "b" ? "#000" : "#bbb"}"/>`;
  }
  for (const [r, c] of ring) out += `<circle cx="${p + c * s}" cy="${p + r * s}" r="11" fill="none" stroke="#e34948" stroke-width="3"/>`;
  return out + "</svg>";
}
function buildLearn() {
  const cards = [
    { t: "Take turns", d: "Black goes first. Then you take turns putting one stone on any empty crossing.", b: miniBoard([[3, 3, "b"], [3, 4, "w"], [4, 4, "b"]]) },
    { t: "Make five in a row", d: "Get 5 of your stones in a line: across ➡️, down ⬇️ or diagonal ↘️ ↗️.", b: miniBoard([[1, 1, "b"], [2, 2, "b"], [3, 3, "b"], [4, 4, "b"], [5, 5, "b"], [2, 4, "w"], [3, 4, "w"]], 7, [[1, 1], [5, 5]]) },
    { t: "Block your opponent", d: "If your opponent has 4 in a row, put a stone at the end to stop them!", b: miniBoard([[3, 1, "w"], [3, 2, "w"], [3, 3, "w"], [3, 4, "w"], [3, 5, "b"], [2, 3, "b"]], 7, [[3, 0]]) },
    { t: "Watch for open threes", d: "Three in a row with empty space on both sides is dangerous. Block one end early.", b: miniBoard([[3, 2, "w"], [3, 3, "w"], [3, 4, "w"], [4, 3, "b"]], 7, [[3, 1], [3, 5]]) },
    { t: "Double attack!", d: "Make two threats at once. Your opponent can only block one of them!", b: miniBoard([[3, 1, "b"], [3, 2, "b"], [3, 3, "b"], [1, 4, "b"], [2, 4, "b"], [4, 5, "w"], [5, 5, "w"]], 7, [[3, 4]]) },
    { t: "Climb the levels", d: "10 levels from 🐣 to 🐉. Boards grow from 9×9 to 15×15. Pause any time, and continue later!", b: `<div style="font-size:44px;padding:26px 0">🐣🦇🦊🐢🦉🐉</div>` },
  ];
  $("learnGrid").innerHTML = cards.map((c, i) => `<div class="learn-card"><span class="step">${i + 1}</span><h3>${c.t}</h3>${c.b}<p>${c.d}</p></div>`).join("");
}
function buildHero() {
  const svg = document.querySelector(".hero-board");
  svg.innerHTML = miniBoard([[1, 1, "b"], [2, 2, "b"], [3, 3, "b"], [4, 4, "b"], [2, 3, "w"], [3, 2, "w"], [4, 3, "w"], [1, 3, "w"], [5, 2, "b"]], 8, [[5, 5]])
    .replace(/^<svg[^>]*>|<\/svg>$/g, "");
  svg.setAttribute("viewBox", "0 0 196 196");
}

/* ------------------------------------------------------------------ start up */
$("soundBtn").onclick = () => setSound(!Sound.on);
$("pSoundBtn").onclick = () => setSound(!Sound.on);
setSound(Sound.on);

Game.view = new BoardView($("board"), { onClick: (r, c) => Game.click(r, c) });
Game.view.canHover = (r, c) => Game.isHumanTurn() && !Game.board[r][c];
Watch.view = new BoardView($("watchBoard"), { numbers: true });

$("hintBtn").onclick = () => Game.hint();
$("undoBtn").onclick = () => Game.undo();
$("newBtn").onclick = async () => {
  if (!Game.inProgress() || await confirmBox("Restart?", "Start this game again from the beginning?")) Game.restart();
};
$("pauseBtn").onclick = () => Game.pause();
$("backBtn").onclick = () => Game.exit();
$("resumeBtn").onclick = () => Game.resume();
$("pRestartBtn").onclick = async () => {
  $("pauseMenu").hidden = true;
  if (await confirmBox("Restart?", "Start this game again from the beginning?")) Game.restart();
  else $("pauseMenu").hidden = false;
};
$("pHelpBtn").onclick = () => { go("learn"); };
$("pExitBtn").onclick = () => Game.exit();
$("pausedCover").onclick = () => Game.resume();

$("againBtn").onclick = () => { $("modal").hidden = true; Game.restart(); };
$("nextLevelBtn").onclick = () => { $("modal").hidden = true; playLevel(Game.levelIdx + 1); };
$("reviewBtn").onclick = () => { $("modal").hidden = true; };
$("menuBtn").onclick = () => go(Game.levelIdx !== null ? "levels" : "home");

document.addEventListener("keydown", (e) => {
  if (e.target.matches("input, select, textarea")) return;
  if (!$("confirm").hidden) { if (e.key === "Escape") $("confirmNo").click(); return; }
  if (e.key === "Escape" && !$("modal").hidden) { $("modal").hidden = true; return; }
  if (currentScreen !== "game") return;
  const k = e.key.toLowerCase();
  if (k === "escape" || k === "p") { Game.paused ? Game.resume() : Game.pause(); e.preventDefault(); }
  else if (Game.paused) return;
  else if (k === "h") Game.hint();
  else if (k === "u") Game.undo();
  else if (k === "r") $("newBtn").click();
});
addEventListener("beforeunload", () => Game.save());
document.addEventListener("visibilitychange", () => { if (document.hidden) Game.save(); });

buildPicker(); buildLearn(); buildHero(); Watch.init(); Lab.init(); Lab.loadAgents();
refreshContinue();
