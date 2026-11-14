/* Gomoku motion layer.
 * Everything animated lives here: smooth scroll, page transitions, reveals,
 * the home hero and the scroll sections. Game logic (app.js) is untouched
 * except that this file wraps the global go() router.
 *
 * Rules: animate transform + opacity only, respect prefers-reduced-motion,
 * lighter variants on touch, no effects at all on the game board. */
"use strict";
(function () {
  const hasGsap = !!(window.gsap && window.ScrollTrigger);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  const fine = window.matchMedia("(hover: hover) and (pointer: fine)");
  const wide = window.matchMedia("(min-width: 861px)");
  const M = (window.Motion = { enabled: hasGsap && !reduce.matches, lenis: null, busy: false });
  const $ = (id) => document.getElementById(id);
  const qa = (sel, root = document) => [...root.querySelectorAll(sel)];
  if (!hasGsap) return;
  gsap.registerPlugin(ScrollTrigger);
  document.documentElement.classList.toggle("motion", M.enabled);
  reduce.addEventListener("change", () => location.reload());

  /* ------------------------------------------------------------ smooth scroll */
  qa(".modal, .move-list").forEach((e) => e.setAttribute("data-lenis-prevent", ""));
  if (M.enabled && window.Lenis) {
    M.lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 0.95, smoothWheel: true });
    M.lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((t) => M.lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
  }
  M.scrollTop = () => { if (M.lenis) M.lenis.scrollTo(0, { immediate: true, force: true }); else scrollTo(0, 0); };

  /* ------------------------------------------------------------ text splitting
   * Wraps each word's characters in masked spans so lines can slide up. The
   * original text stays in aria-label so screen readers read one phrase. */
  M.splitLines = function (el) {
    if (!el || el.dataset.split) return qa(".ch", el);
    const text = el.textContent.trim();
    el.setAttribute("aria-label", text);
    el.dataset.split = "1";
    el.innerHTML = text.split(/\s+/).map((w) =>
      `<span class="w" aria-hidden="true"><span class="ch">${w}</span></span>`).join(" ");
    return qa(".ch", el);
  };
  M.revealWords = function (el, opts = {}) {
    const parts = M.splitLines(el);
    if (!M.enabled) return gsap.timeline();
    return gsap.fromTo(parts, { yPercent: 115 }, { yPercent: 0, duration: opts.duration || 0.9, ease: "expo.out", stagger: opts.stagger ?? 0.07, delay: opts.delay || 0 });
  };

  /* ------------------------------------------------------------ generic reveals
   * Marks elements on the active screen and fades/slides them in once. */
  const REVEAL = {
    pick: [".screen-title", ".screen-sub", ".setup-row", ".smart-card", ".pick-title", ".op-card"],
    levels: [".screen-title", ".progress-row", ".screen-sub", ".level"],
    watch: [".screen-title", ".screen-sub"],
    lab: [".screen-title", ".screen-sub", ".lab-tabs"],
    scores: [".screen-title", ".screen-sub"],
    learn: [".screen-title", ".screen-sub", ".learn-tabs"],
  };
  M.revealScreen = function (name) {
    if (!M.enabled || !REVEAL[name]) return;
    const root = $("screen-" + name);
    const items = REVEAL[name].flatMap((s) => qa(s, root));
    if (!items.length) return;
    gsap.killTweensOf(items);
    gsap.fromTo(items, { opacity: 0, y: 28 }, {
      opacity: 1, y: 0, duration: 0.7, ease: "power3.out", stagger: { each: 0.045, from: "start" },
      clearProps: "transform,opacity",
    });
  };

  /* ------------------------------------------------------------ page transitions
   * A navy curtain wipes up over the old screen, the router swaps screens
   * underneath, then the curtain lifts away. Skipped for reduced motion. */
  const curtain = document.createElement("div");
  curtain.id = "curtain"; curtain.setAttribute("aria-hidden", "true");
  curtain.innerHTML = '<span class="curtain-line"></span>';
  document.body.appendChild(curtain);
  gsap.set(curtain, { yPercent: 100, visibility: "hidden" });

  const baseGo = window.go;
  let current = "home";
  window.go = function (name) {
    // the "friend" shortcut starts a game through the router itself
    if (!M.enabled || M.busy || name === current || name === "friend") {
      const r = baseGo(name);
      afterSwap(name);
      return r;
    }
    M.busy = true;
    const toGame = name === "game", fromGame = current === "game";
    const dur = toGame || fromGame ? 0.32 : 0.42;
    gsap.set(curtain, { visibility: "visible", yPercent: 100, transformOrigin: "50% 100%" });
    gsap.timeline({ defaults: { ease: "power3.inOut" } })
      .to(curtain, { yPercent: 0, duration: dur })
      .add(() => { baseGo(name); M.scrollTop(); afterSwap(name, true); })
      .set(curtain, { transformOrigin: "50% 0%" })
      .to(curtain, { yPercent: -100, duration: dur + 0.1, delay: 0.05 })
      .add(() => { M.busy = false; gsap.set(curtain, { visibility: "hidden" }); if (name !== "game") M.revealScreen(name); document.dispatchEvent(new CustomEvent("screen:shown", { detail: name })); });
  };
  function afterSwap(name, silent) {
    current = document.querySelector(".screen.active")?.id.replace("screen-", "") || name;
    document.body.dataset.screen = current;
    if (M.lenis) { current === "game" ? M.lenis.stop() : M.lenis.start(); }
    ScrollTrigger.refresh();
    if (!silent) document.dispatchEvent(new CustomEvent("screen:shown", { detail: current }));
  }
  document.body.dataset.screen = "home";

  /* modules register themselves here (home hero, sections, cursor...) */
  M.ready = [];
  window.addEventListener("load", () => { M.ready.forEach((fn) => fn()); ScrollTrigger.refresh(); });
  window.addEventListener("resize", () => ScrollTrigger.refresh());
  M.fine = () => fine.matches && M.enabled;
  M.wide = () => wide.matches;
})();
