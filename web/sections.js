/* Home scroll sections: opponents list, engine explainer (pinned, scrubbed),
 * levels track (pinned horizontal on desktop), closing, plus heading reveals.
 * Reads OPPONENTS / LEVELS / Progress from app.js; never touches game logic. */
"use strict";
(function () {
  const M = window.Motion;
  if (!M || !window.gsap) return;
  const $ = (id) => document.getElementById(id);
  const qa = (s, r = document) => [...r.querySelectorAll(s)];
  const NS = "http://www.w3.org/2000/svg";
  const ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
  const LOCK = '<svg class="lock-ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="1.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>';

  /* ---------------------------------------------------------------- opponents */
  function rng(seed) { let a = seed; return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };
  // idle (--h) and hover (--h2) bar heights describe how each engine searches
  function barPattern(kind, seed) {
    const r = rng(seed * 97 + 3), n = 18, idle = [], hov = [];
    for (let i = 0; i < n; i++) {
      idle.push(0.16 + r() * 0.14);
      const g = 1 - Math.abs(i - n * 0.38) / (n * 0.62); // a smooth hill: graded evaluation
      let v;
      if (kind === "rand") v = 0.15 + r() * 0.8;
      else if (kind === "flat") v = 0.42;
      else if (kind === "rules") v = [3, 8, 12].includes(i) ? 0.95 - (i % 3) * 0.08 : 0.12;
      else if (kind === "graded") v = 0.2 + g * 0.75;
      else if (kind === "pruned") v = i % 3 === 2 ? 0.05 : 0.2 + g * 0.75;
      else v = 0.28 + g * 0.7 + r() * 0.08;
      hov.push(Math.max(0.05, Math.min(1, v)));
    }
    const top = hov.indexOf(Math.max(...hov));
    return idle.map((h, i) => `<i style="--i:${i};--h:${h.toFixed(2)};--h2:${hov[i].toFixed(2)}" class="${i === top ? "top" : ""}"></i>`).join("");
  }
  function buildOpponents() {
    const kinds = { Easy: "rand", Blind: "flat", Medium: "rules", Minimax: "graded", Hard: "pruned", Expert: "deep" };
    $("oppList").innerHTML = Object.entries(OPPONENTS).map(([lvl, o], i) => `
      <li><button class="opp" type="button" data-opp="${lvl}" data-cursor="Play">
        <span class="opp-name">${o.name}</span>
        <span class="opp-meta"><b>${o.tier}</b><span>${o.tech}</span></span>
        <span class="opp-bars" aria-hidden="true">${barPattern(kinds[lvl], i + 1)}</span>
        <span class="opp-go" aria-hidden="true">${ARROW}</span>
      </button></li>`).join("");
    $("oppList").addEventListener("click", (e) => {
      const b = e.target.closest("[data-opp]");
      if (b) startGame({ mode: "ai", size: pickSize, level: b.dataset.opp, first: firstMove });
    });
  }

  /* ---------------------------------------------------------------- levels */
  function buildLevels() {
    const d = Progress.data;
    $("lvTrack").innerHTML = LEVELS.map((L, i) => {
      const op = OPPONENTS[L.op], locked = i + 1 > d.unlocked, stars = d.stars[i] || 0;
      return `<button class="lv-card${locked ? " locked" : ""}" type="button" data-lv="${i}" ${locked ? 'aria-disabled="true"' : ""} data-cursor="${locked ? "" : "Start"}">
        <span class="lv-num">${String(i + 1).padStart(2, "0")}</span>
        <span class="lv-body"><b>${L.title}</b><span>${L.size}×${L.size} · vs ${op.name}${L.first === "ai" ? " · engine moves first" : ""}</span></span>
        <span class="lv-foot">${locked ? `${LOCK}<span>Locked</span>` : `<span>${stars ? "Completed" : "Open"}</span><span class="lv-stars" aria-label="${stars} of 3 stars">${[1, 2, 3].map((s) => `<span class="${s <= stars ? "" : "off"}">★</span>`).join("")}</span>`}</span>
      </button>`;
    }).join("");
  }
  $("lvTrack").addEventListener("click", (e) => {
    const b = e.target.closest("[data-lv]"); if (!b) return;
    const i = +b.dataset.lv;
    if (i + 1 > Progress.data.unlocked) { Sound.oops(); toast(`Beat level ${i} first to unlock this one.`); return; }
    playLevel(i);
  });

  /* ---------------------------------------------------------------- engine explainer */
  const CELL = 44, PAD = 36;
  const xy = (r, c) => [PAD + c * CELL, PAD + r * CELL];
  const BLACK = [[4, 3], [4, 4], [4, 5]], WHITE = [[3, 3], [5, 5], [3, 6]];
  const CAND = [[4, 2, 92], [4, 6, 88], [3, 4, 41], [5, 4, 38], [3, 5, 30], [5, 3, 27], [5, 2, 18], [2, 4, 12], [6, 5, 10], [2, 2, 8]];
  function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent && parent.appendChild(e); return e; }
  function buildEngine() {
    const svg = $("engSvg"); svg.innerHTML = "";
    svg.insertAdjacentHTML("beforeend", `<defs>
      <radialGradient id="eg-b" cx=".34" cy=".3" r=".8"><stop offset="0" stop-color="#4a5468"/><stop offset=".5" stop-color="#171d2b"/><stop offset="1" stop-color="#05080f"/></radialGradient>
      <radialGradient id="eg-w" cx=".34" cy=".3" r=".85"><stop offset="0" stop-color="#fff"/><stop offset=".6" stop-color="#f3f6f8"/><stop offset="1" stop-color="#cbd6de"/></radialGradient>
      <filter id="eg-sh" x="-30%" y="-30%" width="170%" height="170%"><feDropShadow dx="0" dy="1.6" stdDeviation="1.6" flood-color="#0b1e3a" flood-opacity=".35"/></filter></defs>`);
    el("rect", { x: 0.5, y: 0.5, width: 423, height: 423, rx: 4, class: "e-surface" }, svg);
    const end = PAD + 8 * CELL;
    for (let i = 0; i < 9; i++) { const p = PAD + i * CELL; el("line", { x1: PAD, y1: p, x2: end, y2: p, class: "e-line" }, svg); el("line", { x1: p, y1: PAD, x2: p, y2: end, class: "e-line" }, svg); }
    const stone = (r, c, col, parent, extra = {}) => { const [x, y] = xy(r, c); return el("circle", { cx: x, cy: y, r: 17, fill: `url(#eg-${col})`, filter: "url(#eg-sh)", stroke: col === "b" ? "rgba(255,255,255,.2)" : "rgba(11,30,58,.22)", ...extra }, parent); };
    const gStones = el("g", {}, svg);
    BLACK.forEach(([r, c]) => stone(r, c, "b", gStones)); WHITE.forEach(([r, c]) => stone(r, c, "w", gStones));
    const L = (name) => el("g", { class: name }, svg);
    const gCand = L("l-cand"), gScore = L("l-score"), gLook = L("l-look"), gPrune = L("l-prune"), gBest = L("l-best");
    const rings = CAND.map(([r, c]) => { const [x, y] = xy(r, c); return el("circle", { cx: x, cy: y, r: 18, class: "e-cand" }, gCand); });
    const scores = CAND.map(([r, c, s]) => { const [x, y] = xy(r, c); const t = el("text", { x, y: y + 4.5, class: "e-score" }, gScore); t.textContent = s; return t; });
    // look-ahead: best candidate, black's reply, white's follow-up, drawn as a path with ghost stones
    const [bx, by] = xy(4, 2), [rx, ry] = xy(4, 6), [fx, fy] = xy(2, 4);
    const p1 = el("path", { d: `M${bx} ${by - 22} Q ${(bx + rx) / 2} ${by - 96} ${rx} ${ry - 22}`, class: "e-look", pathLength: 1 }, gLook);
    const p2 = el("path", { d: `M${rx} ${ry - 22} Q ${(rx + fx) / 2 + 30} ${ry - 84} ${fx + 18} ${fy + 8}`, class: "e-look", pathLength: 1 }, gLook);
    const g1 = stone(4, 6, "b", gLook, { opacity: 0.5, filter: "none" }), g2 = stone(2, 4, "w", gLook, { opacity: 0.5, filter: "none" });
    const lab = (x, y, t) => { const e = el("text", { x, y, class: "e-score" }, gLook); e.textContent = t; return e; };
    const l1 = lab(rx, ry + 4.5, "2"), l2 = lab(fx, fy + 4.5, "3");
    // pruned: low-scoring branches crossed out
    const prunes = CAND.filter((c) => c[2] <= 18).map(([r, c]) => { const [x, y] = xy(r, c); return el("path", { d: `M${x - 9} ${y - 9} L${x + 9} ${y + 9} M${x + 9} ${y - 9} L${x - 9} ${y + 9}`, class: "e-prune", pathLength: 1 }, gPrune); });
    const pruneRings = rings.filter((_, i) => CAND[i][2] <= 18);
    // best move
    const bestStone = stone(4, 2, "w", gBest);
    const bestRing = el("circle", { cx: bx, cy: by, r: 22, class: "e-best" }, gBest);
    return { rings, scores, p1, p2, g1, g2, l1, l2, prunes, pruneRings, bestStone, bestRing };
  }
  function engineTimeline(p) {
    const tl = gsap.timeline({ defaults: { ease: "power2.out" } });
    const dash = (e) => gsap.set(e, { strokeDasharray: 1, strokeDashoffset: 1 });
    [p.p1, p.p2, ...p.prunes].forEach(dash);
    gsap.set([p.rings, p.scores, p.g1, p.g2, p.l1, p.l2, p.bestStone, p.bestRing].flat(), { opacity: 0, transformOrigin: "50% 50%" });
    tl.to(p.rings, { opacity: 1, scale: 1, duration: 0.6, stagger: 0.05 }, 0)
      .fromTo(p.rings, { scale: 0.5 }, { scale: 1, duration: 0.6, stagger: 0.05 }, 0)
      .to(p.scores, { opacity: 1, duration: 0.6, stagger: 0.05 }, 1)
      .to(p.p1, { strokeDashoffset: 0, duration: 0.5 }, 2).to([p.g1, p.l1], { opacity: 1, duration: 0.3 }, 2.4)
      .to(p.p2, { strokeDashoffset: 0, duration: 0.5 }, 2.5).to([p.g2, p.l2], { opacity: 1, duration: 0.3 }, 2.9)
      .to(p.prunes, { strokeDashoffset: 0, duration: 0.3, stagger: 0.08 }, 3)
      .to(p.pruneRings, { opacity: 0.18, duration: 0.4 }, 3)
      .to([p.g1, p.g2, p.l1, p.l2, p.p1, p.p2], { opacity: 0.25, duration: 0.4 }, 3.35)
      .to(p.bestRing, { opacity: 1, duration: 0.3 }, 3.5)
      .fromTo(p.bestStone, { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.4 }, 3.55);
    tl.duration(4.2);
    return tl;
  }

  /* ---------------------------------------------------------------- headings */
  function headings() {
    qa("[data-split]").forEach((h) => {
      const parts = M.splitLines(h);
      if (!M.enabled) return;
      gsap.set(parts, { yPercent: 115 });
      ScrollTrigger.create({ trigger: h, start: "top 88%", once: true, onEnter: () => gsap.to(parts, { yPercent: 0, duration: 1, ease: "expo.out", stagger: 0.09 }) });
    });
  }

  /* ---------------------------------------------------------------- boot */
  buildOpponents(); buildLevels();
  M.ready.push(() => {
    headings();
    const parts = buildEngine();
    const items = qa("#engList li");
    const setStep = (i) => items.forEach((li, k) => li.classList.toggle("on", k === i));
    const mm = gsap.matchMedia();
    mm.add({ desk: "(min-width: 861px) and (prefers-reduced-motion: no-preference)", rest: "(max-width: 860px), (prefers-reduced-motion: reduce)" }, (ctx) => {
      if (ctx.conditions.desk) {
        // opponents: rows rise in
        gsap.set(".opp", { opacity: 0, y: 40 });
        ScrollTrigger.batch(".opp", { start: "top 94%", once: true, onEnter: (b) => gsap.to(b, { opacity: 1, y: 0, duration: 0.8, ease: "power3.out", stagger: 0.08, overwrite: true }) });
        // engine: pinned and scrubbed through four steps
        const tl = engineTimeline(parts);
        ScrollTrigger.create({
          trigger: "#engPin", start: "top top", end: "+=260%", pin: true, scrub: 0.6, animation: tl, anticipatePin: 1,
          onUpdate: (self) => setStep(Math.min(3, Math.floor(self.progress * 4 - 0.001))),
          onEnter: () => setStep(0), onLeaveBack: () => setStep(-1),
        });
        setStep(0);
        // levels: pinned horizontal track
        const track = $("lvTrack");
        gsap.to(track, { x: () => -(track.scrollWidth - innerWidth + 1), ease: "none", scrollTrigger: { trigger: "#hLevels", start: "top top", end: () => "+=" + (track.scrollWidth - innerWidth), pin: true, scrub: 0.6, invalidateOnRefresh: true, anticipatePin: 1 } });
      } else {
        // phones and reduced motion: static final state, native scrolling
        engineTimeline(parts).progress(1).kill();
        items.forEach((li) => li.classList.add("on"));
      }
    });
    document.fonts.ready.then(() => ScrollTrigger.refresh()); setTimeout(() => ScrollTrigger.refresh(), 2500);
  });
  document.addEventListener("screen:shown", (e) => { if (e.detail === "home") { buildLevels(); ScrollTrigger.refresh(); } });

  /* cursor flips to ink on the paper section */
  document.addEventListener("pointerover", (e) => {
    const c = $("cursor"); if (!c) return;
    c.classList.toggle("ink", !!(e.target.closest && e.target.closest('[data-surface="paper"]')));
  });
})();
