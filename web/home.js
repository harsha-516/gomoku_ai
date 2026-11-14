/* Home page motion: loader, hero (pseudo-3D board), marquee, custom cursor.
 *
 * The hero board is isolated behind Motion.heroBoard {init, destroy} so it can
 * later be replaced by a desktop-only Three.js scene without touching the rest. */
"use strict";
(function () {
  const M = window.Motion;
  if (!M || !window.gsap) return;
  const $ = (id) => document.getElementById(id);
  const qa = (s, r = document) => [...r.querySelectorAll(s)];
  const html = document.documentElement;

  /* ---------------------------------------------------------------- hero board */
  const CELL = 56, PAD = 56, N = 9, TILT_X = 52, TILT_Z = -30, LIFT = 22;
  // a short game: Black makes four, White blocks one end, Black completes five on the other
  const MOVES = [[4, 4, "b"], [3, 3, "w"], [4, 5, "b"], [5, 5, "w"], [4, 3, "b"], [3, 6, "w"], [4, 6, "b"], [4, 2, "w"], [4, 7, "b"]];
  const WIN = [[4, 3], [4, 7]];
  const px = (r, c) => [PAD + c * CELL, PAD + r * CELL];

  const HeroBoard = (M.heroBoard = {
    tl: null, nodes: [], moveParallax: null,
    init() {
      const plane = $("hPlane"), rig = $("hRig");
      if (!plane || plane.dataset.ready) return;
      plane.dataset.ready = "1";
      const end = PAD + (N - 1) * CELL;
      let g = "";
      for (let i = 0; i < N; i++) {
        const p = PAD + i * CELL;
        g += `<line x1="${PAD}" y1="${p}" x2="${end}" y2="${p}"/><line x1="${p}" y1="${PAD}" x2="${p}" y2="${end}"/>`;
      }
      for (const [r, c] of [[2, 2], [2, 6], [4, 4], [6, 2], [6, 6]]) { const [x, y] = px(r, c); g += `<circle cx="${x}" cy="${y}" r="3.5" class="hstar"/>`; }
      plane.innerHTML = `<svg viewBox="0 0 560 560" aria-hidden="true"><g stroke="#2a4258" stroke-width="1">${g}</g><style>.hstar{fill:#1f3346}</style></svg>`;

      // elements: shadow (flat on the board), stone (billboard facing the camera), ring + win bar (flat)
      const mk = (cls) => { const d = document.createElement("div"); d.className = cls; plane.appendChild(d); return d; };
      this.nodes = MOVES.map(([r, c, col]) => ({ r, c, col, sh: mk("hs-sh"), st: mk("hs " + col) }));
      this.ring = mk("hs-ring");
      this.bar = mk("hs-win");
      const [x1, y1] = px(...WIN[0]), [x2] = px(...WIN[1]);
      gsap.set(this.bar, { x: x1, y: y1, width: x2 - x1 });
      gsap.set(this.ring, { opacity: 0 });
      gsap.set(this.bar, { opacity: 0 });
      this.nodes.forEach((n) => {
        const [x, y] = px(n.r, n.c);
        gsap.set(n.sh, { x, y, opacity: 0 });
        gsap.set(n.st, { x, y, z: LIFT, rotation: -TILT_Z, rotationX: -TILT_X, opacity: 0 });
      });
      gsap.set(rig, { rotationX: TILT_X, rotationZ: TILT_Z, transformOrigin: "50% 50%" });
      this.fit();
      this.ro = new ResizeObserver(() => this.fit());
      this.ro.observe(rig.closest(".h-stage"));
      if (!M.enabled) this.showFinal();
    },
    fit() {
      const stage = $("hRig").closest(".h-stage"), w = stage.clientWidth;
      stage.style.setProperty("--hs", (w / 700).toFixed(4));
    },
    showFinal() {
      this.nodes.forEach((n) => { gsap.set(n.st, { opacity: 1 }); gsap.set(n.sh, { opacity: 1 }); });
      gsap.set(this.bar, { opacity: 1, scaleX: 1 });
      const [x, y] = px(MOVES[MOVES.length - 1][0], MOVES[MOVES.length - 1][1]);
      gsap.set(this.ring, { x, y, opacity: 1 });
    },
    play() {
      if (!M.enabled || this.tl) return this.tl && this.tl.play();
      const tl = (this.tl = gsap.timeline({ repeat: -1, repeatDelay: 0.5, delay: 0.5 }));
      const STEP = 0.7;
      this.nodes.forEach((n, i) => {
        const t = i * STEP, [x, y] = px(n.r, n.c);
        tl.fromTo(n.st, { z: LIFT + 230, opacity: 0 }, { z: LIFT, opacity: 1, duration: 0.55, ease: "power2.in" }, t)
          .fromTo(n.sh, { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.55, ease: "power2.in" }, t)
          .set(this.ring, { x, y }, t + 0.55)
          .fromTo(this.ring, { opacity: 0, scale: 1.35 }, { opacity: 1, scale: 1, duration: 0.3, ease: "power2.out" }, t + 0.55);
      });
      const tEnd = MOVES.length * STEP + 0.3;
      tl.to(this.ring, { opacity: 0, duration: 0.2 }, tEnd - 0.1)
        .fromTo(this.bar, { opacity: 1, scaleX: 0 }, { scaleX: 1, duration: 0.7, ease: "power3.inOut" }, tEnd)
        .to(this.nodes.filter((n) => n.r === 4 && n.col === "b" && n.c >= 3).map((n) => n.st), { scale: 1.08, duration: 0.3, yoyo: true, repeat: 1, ease: "sine.inOut" }, tEnd + 0.2)
        .to([this.bar, ...this.nodes.flatMap((n) => [n.st, n.sh])], { opacity: 0, duration: 0.7, ease: "power1.inOut" }, tEnd + 2.6);
      // pause when the hero is off screen or the tab is hidden
      ScrollTrigger.create({ trigger: "#hHero", start: "top bottom", end: "bottom top", onToggle: (s) => tl.paused(!s.isActive) });
      document.addEventListener("visibilitychange", () => tl.paused(document.hidden));
      document.addEventListener("screen:shown", (e) => tl.paused(e.detail !== "home"));
    },
    parallax() {
      if (!M.fine()) { if (M.enabled) this.watch(null); return; }
      // pointer tilt: ease toward the target on the shared ticker (no per-event tweens)
      const rig = $("hRig"); let tx = TILT_X, tz = TILT_Z, cx = TILT_X, cz = TILT_Z, visible = true;
      ScrollTrigger.create({ trigger: "#hHero", start: "top bottom", end: "bottom top", onToggle: (s) => { visible = s.isActive; } });
      window.addEventListener("pointermove", (e) => {
        if (document.body.dataset.screen !== "home") return;
        const nx = e.clientX / innerWidth - 0.5, ny = e.clientY / innerHeight - 0.5;
        tx = TILT_X - ny * 9; tz = TILT_Z + nx * 12;
      }, { passive: true });
      gsap.ticker.add(() => {
        if (!visible || (Math.abs(tx - cx) < 0.01 && Math.abs(tz - cz) < 0.01)) return;
        cx += (tx - cx) * 0.07; cz += (tz - cz) * 0.07;
        gsap.set(rig, { rotationX: cx, rotationZ: cz });
      });
      const float = gsap.to(".h-stage", { y: 12, duration: 4.2, ease: "sine.inOut", yoyo: true, repeat: -1 });
      this.watch(float);
    },
    // once the hero is off screen, stop its tweens and drop its 3D layers from compositing
    watch(float) {
      const stage = document.querySelector(".h-stage");
      ScrollTrigger.create({ trigger: "#hHero", start: "top bottom", end: "bottom top", onToggle: (s) => {
        if (float) float.paused(!s.isActive);
        if (stage) stage.style.visibility = s.isActive ? "visible" : "hidden";
      } });
    },
    destroy() { if (this.tl) this.tl.kill(); if (this.ro) this.ro.disconnect(); },
  });

  /* ---------------------------------------------------------------- marquee */
  function marquee() {
    const track = $("mqTrack"); if (!track) return;
    const words = ["Random", "Blind search", "Rule-based", "Minimax", "Alpha-beta pruning", "Iterative deepening", "Transposition table", "Heuristic evaluation"];
    const one = words.map((w, i) => `<span class="mq-item${i % 2 ? " dim" : ""}">${w}<i class="mq-dot ${i % 2 ? "w" : "b"}"></i></span>`).join("");
    track.innerHTML = one + one;
    if (!M.enabled) return;
    const tween = gsap.to(track, { xPercent: -50, duration: 46, ease: "none", repeat: -1 });
    let dir = 1;
    ScrollTrigger.create({
      onUpdate(self) {
        dir = self.direction;
        const boost = Math.min(Math.abs(self.getVelocity()) / 250, 7);
        gsap.to(tween, { timeScale: dir * (1 + boost), duration: 0.25, overwrite: true });
        gsap.to(tween, { timeScale: dir, duration: 1.1, delay: 0.25, overwrite: "auto" });
      },
    });
    const bar = track.closest(".marquee");
    bar.addEventListener("pointerenter", () => gsap.to(tween, { timeScale: 0.15 * dir, duration: 0.5, overwrite: true }));
    bar.addEventListener("pointerleave", () => gsap.to(tween, { timeScale: dir, duration: 0.6, overwrite: true }));
  }

  /* ---------------------------------------------------------------- hero entrance + loader */
  function heroIn() {
    HeroBoard.init(); HeroBoard.parallax();
    const title = $("hTitle");
    if (!M.enabled) return;
    const tl = gsap.timeline();
    tl.add(M.revealWords(title, { stagger: 0.12, duration: 1.15 }), 0)
      .fromTo(".h-lede, .h-cta, .continue-info, .player-chip", { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.8, ease: "power3.out", stagger: 0.09, clearProps: "transform,opacity" }, 0.45)
      .fromTo("#hRig", { opacity: 0, y: 120 }, { opacity: 1, y: 0, duration: 1.5, ease: "expo.out" }, 0.1)
      .fromTo(".h-scroll", { opacity: 0 }, { opacity: 1, duration: 0.8 }, 1.1)
      .add(() => HeroBoard.play(), 0.9);
  }
  function runLoader(done) {
    const L = $("loader"), cnt = $("ldCount"), o = { v: 0 };
    try { sessionStorage.setItem("g-intro", "1"); } catch {}
    if (M.lenis) M.lenis.stop();
    let finished = false;
    const finish = () => {
      if (finished) return; finished = true;
      html.classList.remove("intro-run");
      gsap.to(L, { yPercent: -100, duration: 0.85, ease: "expo.inOut", onComplete: () => { html.classList.remove("intro"); gsap.set(L, { clearProps: "all" }); if (M.lenis) M.lenis.start(); } });
      gsap.delayedCall(0.38, done);
    };
    const tl = gsap.timeline({ onComplete: finish });
    tl.to(".ld-bar", { scaleX: 1, duration: 1.45, ease: "power2.inOut" }, 0)
      .to(o, { v: 100, duration: 1.45, ease: "power2.inOut", onUpdate: () => { cnt.textContent = String(Math.round(o.v)).padStart(3, "0"); } }, 0)
      .fromTo(".ld-s.b", { y: -46, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: "power2.in" }, 0.15)
      .fromTo(".ld-s.w", { y: -46, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: "power2.in" }, 0.7)
      .to({}, { duration: 0.15 });
    const skip = () => { tl.kill(); o.v = 100; cnt.textContent = "100"; finish(); };
    $("ldSkip").addEventListener("click", skip);
    window.addEventListener("keydown", (e) => { if (!finished && (e.key === "Escape" || e.key === "Enter" || e.key === " ")) skip(); });
    if (M.skipRequested) skip();   // the visitor already pressed Skip while fonts were loading
  }

  /* ---------------------------------------------------------------- custom cursor */
  function cursor() {
    if (!M.fine()) return;
    html.classList.add("has-cursor");
    const root = $("cursor"), ring = root.querySelector(".cur-ring"), label = ring.querySelector("em");
    gsap.set(root, { opacity: 0 });
    const dx = gsap.quickTo(root.querySelector(".cur-dot"), "x", { duration: 0.12, ease: "power3.out" });
    const dy = gsap.quickTo(root.querySelector(".cur-dot"), "y", { duration: 0.12, ease: "power3.out" });
    const rx = gsap.quickTo(ring, "x", { duration: 0.45, ease: "power3.out" });
    const ry = gsap.quickTo(ring, "y", { duration: 0.45, ease: "power3.out" });
    let shown = false;
    window.addEventListener("pointermove", (e) => {
      if (!shown) { shown = true; gsap.to(root, { opacity: 1, duration: 0.3 }); gsap.set([root.querySelector(".cur-dot"), ring], { x: e.clientX, y: e.clientY }); }
      dx(e.clientX); dy(e.clientY); rx(e.clientX); ry(e.clientY);
    }, { passive: true });
    document.addEventListener("mouseleave", () => { shown = false; gsap.to(root, { opacity: 0, duration: 0.2 }); });
    const HOT = "a, button, [data-cursor], .level, .op-card, .tab, .seg-btn, label, summary";
    let active = null;
    document.addEventListener("pointerover", (e) => {
      const el = e.target.closest && e.target.closest(HOT);
      if (el === active) return;
      active = el;
      if (!el || el.disabled) { ring.classList.remove("on"); gsap.to(ring, { scale: 1, duration: 0.3, ease: "power3.out" }); gsap.to(label, { opacity: 0, duration: 0.15 }); return; }
      const text = el.dataset.cursor || "";
      const s = text ? 2.3 : 1.7;
      ring.classList.toggle("on", !!text);
      label.textContent = text;
      gsap.to(ring, { scale: s, duration: 0.35, ease: "power3.out" });
      gsap.to(label, { opacity: text ? 1 : 0, scale: 1 / s, duration: 0.25 });
    });
    window.addEventListener("pointerdown", () => gsap.to(ring, { scale: "-=0.25", duration: 0.12 }));
    window.addEventListener("pointerup", () => gsap.to(ring, { scale: active ? (active.dataset.cursor ? 2.3 : 1.7) : 1, duration: 0.2 }));
  }

  /* ---------------------------------------------------------------- boot */
  M.ready.push(() => {
    marquee(); cursor();
    const start = () => heroIn();
    // never let a slow font CDN hold the intro: wait for fonts at most 1.2s, then go
    const fontsOrTimeout = () => Promise.race([document.fonts ? document.fonts.ready : Promise.resolve(), new Promise((r) => setTimeout(r, 1200))]);
    if (M.enabled && html.classList.contains("intro")) {
      $("ldSkip").addEventListener("click", () => { M.skipRequested = true; });
      window.addEventListener("keydown", (e) => { if (e.key === "Escape" || e.key === "Enter") M.skipRequested = true; });
      html.classList.add("intro-run"); fontsOrTimeout().then(() => runLoader(start)); }
    else { html.classList.remove("intro"); fontsOrTimeout().then(start); }
  });
})();
