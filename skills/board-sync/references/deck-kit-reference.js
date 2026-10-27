/* deck-kit.js — explainer moves for imported deck cards (HyperFrames + GSAP, seek-safe).
 * Loaded in the host <head> after gsap and banger-kit.js; scenes call window.DK.* on their timeline.
 * Everything is transforms / opacity / clip-path / filter or per-frame tl.set rows.
 */
(function () {
  const FPS = 30, F = 1 / FPS;
  const DK = {
    FPS, F,
    // ── reveals (set the hidden state at t0 so frame 0 is clean) ──
    // baseline at build time (a hiding tl.set at 0 trips HyperFrames lint; gsap.set + immediateRender:false is the contract)
    hide(sels) { gsap.set(sels, { opacity: 0 }); },
    rise(tl, sel, t, { y = 36, dur = 0.5, ease = "power3.out" } = {}) {
      tl.fromTo(sel, { opacity: 0, y }, { opacity: 1, y: 0, duration: dur, ease, immediateRender: false }, t);
    },
    snap(tl, sel, t, { x = -60, dur = 0.4, ease = "expo.out" } = {}) {
      tl.fromTo(sel, { opacity: 0, x }, { opacity: 1, x: 0, duration: dur, ease, immediateRender: false }, t);
    },
    pop(tl, sel, t, { from = 0.4, dur = 0.38 } = {}) {
      tl.fromTo(sel, { opacity: 0, scale: from }, { opacity: 1, scale: 1, duration: dur, ease: "back.out(2.2)", immediateRender: false }, t);
    },
    slam(tl, sel, t, { from = 2.2, blur = 14, dur = 0.3 } = {}) {
      tl.fromTo(sel, { opacity: 0, scale: from, filter: `blur(${blur}px)` }, { opacity: 1, scale: 1, filter: "blur(0px)", duration: dur, ease: "expo.out", immediateRender: false }, t);
    },
    wipe(tl, sel, t, { dur = 0.45, ease = "power3.inOut" } = {}) {
      tl.set(sel, { opacity: 1 }, t);
      tl.fromTo(sel, { clipPath: "inset(0% 100% 0% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: dur, ease, immediateRender: false }, t);
    },
    wipeUp(tl, sel, t, { dur = 0.5, y = 50 } = {}) {
      tl.set(sel, { opacity: 1 }, t);
      tl.fromTo(sel, { clipPath: "inset(100% 0% 0% 0%)", y }, { clipPath: "inset(0% 0% 0% 0%)", y: 0, duration: dur, ease: "power4.out", immediateRender: false }, t);
    },
    // callout line growing from its anchor: axis "y" (origin top) or "x" (origin right/left)
    grow(tl, sel, t, { dur = 0.32, axis = "y", origin = "top center" } = {}) {
      tl.set(sel, { opacity: 1, transformOrigin: origin }, t);
      const from = axis === "y" ? { scaleY: 0 } : { scaleX: 0 };
      const to = axis === "y" ? { scaleY: 1 } : { scaleX: 1 };
      tl.fromTo(sel, from, { ...to, duration: dur, ease: "power3.out", immediateRender: false }, t);
    },
    // handwriting / underline write-on (left → right)
    write(tl, sel, t, { dur = 0.9 } = {}) {
      tl.set(sel, { opacity: 1 }, t);
      tl.fromTo(sel, { clipPath: "inset(-25% 100% -25% -2%)" }, { clipPath: "inset(-25% -2% -25% -2%)", duration: dur, ease: "none", immediateRender: false }, t);
    },
    // SVG stroke draw-on (deterministic: lengths measured once at build)
    draw(tl, sel, t, { dur = 0.5, ease = "power2.inOut" } = {}) {
      document.querySelectorAll(sel).forEach((p) => {
        const L = p.getTotalLength();
        p.style.strokeDasharray = `${L} ${L}`;
        p.style.strokeDashoffset = `${L}`;
        tl.fromTo(p, { strokeDashoffset: L }, { strokeDashoffset: 0, duration: dur, ease, immediateRender: false }, t);
      });
    },
    // ── UI demo moves ──
    typewriter(tl, sel, t, text, { cps = 70, caret = "▌" } = {}) {
      const frames = Math.max(1, Math.round((text.length / cps) * FPS));
      for (let f = 0; f <= frames; f++) {
        const n = Math.round((f / frames) * text.length);
        tl.set(sel, { textContent: n <= 0 ? "​" : text.slice(0, n) + (n < text.length ? caret : "") }, t + f * F);
      }
    },
    moveTo(tl, sel, t, x, y, { dur = 0.6, ease = "power3.inOut" } = {}) {
      tl.to(sel, { x, y, duration: dur, ease }, t);
    },
    click(tl, sel, t) {
      tl.to(sel, { scale: 0.82, duration: 0.08, ease: "power2.in" }, t);
      tl.to(sel, { scale: 1, duration: 0.14, ease: "back.out(2)" }, t + 0.08);
    },
    // progress bar: element styled width:100% + transform-origin left, scaleX to pct
    barTo(tl, sel, t, pct, { dur = 0.6, ease = "power2.out" } = {}) {
      tl.set(sel, { transformOrigin: "left center" }, 0);
      tl.to(sel, { scaleX: pct, duration: dur, ease }, t);
    },
    textAt(tl, sel, t, text) { tl.set(sel, { textContent: text }, t); },
    styleAt(tl, sel, t, props) { tl.set(sel, props, t); },
    // ── attention ──
    // accent ring/glow pulse on a UI element (box-shadow is paint, not layout)
    ring(tl, sel, t, { color = "rgba(59,139,255,0.55)", dur = 0.9 } = {}) {
      tl.fromTo(sel, { boxShadow: `0 0 0 0px ${color}` }, { boxShadow: `0 0 0 14px rgba(0,0,0,0)`, duration: dur, ease: "power2.out", immediateRender: false }, t);
    },
    dim(tl, sel, t, { to = 0.35, dur = 0.3 } = {}) { tl.to(sel, { opacity: to, duration: dur, ease: "power2.out" }, t); },
    undim(tl, sel, t, { dur = 0.3 } = {}) { tl.to(sel, { opacity: 1, duration: dur, ease: "power2.out" }, t); },
    flicker(tl, sel, t) {
      tl.set(sel, { opacity: 0.35, x: 6 }, t).set(sel, { opacity: 1, x: -4 }, t + F).set(sel, { opacity: 0.6, x: 2 }, t + 2 * F).set(sel, { opacity: 1, x: 0 }, t + 3 * F);
    },
    // slow push on a scene's camera wrapper (one per scene)
    push(tl, sel, t, dur, { to = 1.04 } = {}) {
      tl.fromTo(sel, { scale: 1 }, { scale: to, duration: dur, ease: "none", immediateRender: false }, t);
    },
  };
  window.DK = DK;
})();
