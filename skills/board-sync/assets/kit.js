/* board-sync kit: the move library on ONE paused GSAP timeline, built from the inlined cues (window.__BOARD).
 *
 * Moves: rise, wipe (clip-path), grow (scaleY from the bottom), growx, pop (from 0.82, back.out), write (handwriting
 * reveal with a slight overshoot), draw (SVG stroke via strokeDasharray/strokeDashoffset, lengths measured once),
 * stamp (1.5x then settle; 1.22x cap over 70 px), hide, note (creates the note element), highlight (the headline's
 * marker word pops once on its word), label (on screen from the first frame).
 *
 * Seek-only and deterministic: no Date.now, no Math.random, no CSS animations or transitions, no GSAP plugins.
 * Nothing moves after it lands: every tween ends in the element's resting state, no repeats, no yoyos.
 * Exposes window.__seek(t) (async), window.__dur, window.__ready (Promise), window.__tl.
 */
(function () {
  "use strict";
  const D = window.__BOARD || { dur: 0, cues: [], units: {} };
  const root = document.querySelector(".m-root");
  const style = document.createElement("style");
  style.textContent = "*{animation:none!important;transition:none!important}";
  document.head.appendChild(style);
  if (!root || !window.gsap) {
    window.__dur = D.dur;
    window.__ready = Promise.resolve(false);
    window.__seek = async () => {};
    return;
  }

  // ── media never plays on its own: the seek drives it ──
  const videos = Array.from(root.querySelectorAll("video"));
  videos.forEach((v) => {
    v.removeAttribute("autoplay");
    v.autoplay = false;
    v.muted = true;
    v.preload = "auto";
    try { v.pause(); } catch (e) {}
  });

  // ── units: find each by its element path from the root ──
  const byPath = (p) => {
    let e = root;
    for (const i of p || []) {
      if (!e || !e.children[i]) return null;
      e = e.children[i];
    }
    return e === root ? null : e;
  };
  const EL = {};
  const BASE = new Map(); // resting opacity of each element (a dashed rail at 0.6 stays at 0.6)
  Object.keys(D.units || {}).forEach((id) => {
    const u = D.units[id];
    const e = byPath(u.path);
    if (!e) return;
    e.setAttribute("data-u", id);
    EL[id] = e;
    BASE.set(e, parseFloat(getComputedStyle(e).opacity) || 1);
    if (typeof u.rotation === "number") {
      // an inline rotate() becomes GSAP's, so GSAP can compose its own scale / y with it
      e.style.transform = "";
      gsap.set(e, { rotation: u.rotation });
    }
  });
  const rest = (e) => (BASE.has(e) ? BASE.get(e) : 1);

  const tl = gsap.timeline({ paused: true });
  const AT = (x) => Math.max(0, Number(x) || 0);

  // ── moves ──
  const M = {
    rise(e, t) {
      gsap.set(e, { opacity: 0 });
      tl.fromTo(e, { opacity: 0, y: 14 }, { opacity: rest(e), y: 0, duration: 0.4, ease: "power3.out", immediateRender: false }, t);
    },
    wipe(e, t, dur) {
      gsap.set(e, { opacity: 0 });
      tl.set(e, { opacity: rest(e) }, t);
      tl.fromTo(e, { clipPath: "inset(-20% 100% -20% -2%)" },
        { clipPath: "inset(-20% -2% -20% -2%)", duration: dur || 0.35, ease: "power2.out", immediateRender: false }, t);
      tl.set(e, { clipPath: "none" }, t + (dur || 0.35));
    },
    grow(e, t) {
      gsap.set(e, { opacity: 0, transformOrigin: "50% 100%", scaleY: 0 });
      tl.set(e, { opacity: rest(e) }, t);
      tl.fromTo(e, { scaleY: 0 }, { scaleY: 1, duration: 0.55, ease: "power3.out", immediateRender: false }, t);
    },
    growx(e, t) {
      gsap.set(e, { opacity: 0, transformOrigin: "0% 50%", scaleX: 0 });
      tl.set(e, { opacity: rest(e) }, t);
      tl.fromTo(e, { scaleX: 0 }, { scaleX: 1, duration: 0.55, ease: "power3.out", immediateRender: false }, t);
    },
    pop(e, t, from) {
      gsap.set(e, { opacity: 0 });
      tl.fromTo(e, { opacity: 0, scale: from || 0.82 }, { opacity: rest(e), scale: 1, duration: 0.38, ease: "back.out(2.2)", immediateRender: false }, t);
    },
    write(e, t, dur) {
      // handwriting: a left-to-right reveal with a slight overshoot settle
      const fs = parseFloat(getComputedStyle(e).fontSize) || 40;
      const d = dur || (fs > 60 ? 0.6 : 0.5);
      gsap.set(e, { opacity: 0 });
      tl.set(e, { opacity: rest(e) }, t);
      tl.fromTo(e, { clipPath: "inset(-25% 100% -25% -2%)" },
        { clipPath: "inset(-25% -4% -25% -2%)", duration: d, ease: "power1.inOut", immediateRender: false }, t);
      tl.fromTo(e, { scale: 0.96 }, { scale: 1, duration: d + 0.15, ease: "back.out(1.6)", immediateRender: false }, t);
      tl.set(e, { clipPath: "none" }, t + d);
    },
    draw(e, t) {
      const shapes = Array.from(e.querySelectorAll("path,line,polyline,polygon,circle,ellipse,rect"));
      gsap.set(e, { opacity: 0 });
      tl.set(e, { opacity: rest(e) }, t);
      const n = shapes.length || 1;
      const stagger = Math.min(0.08, 0.35 / n);
      shapes.forEach((s, k) => {
        const cs = getComputedStyle(s);
        const stroked = cs.stroke && cs.stroke !== "none" && (parseFloat(cs.strokeWidth) || 0) > 0;
        const dashed = cs.strokeDasharray && cs.strokeDasharray !== "none";
        let L = 0;
        try { L = s.getTotalLength(); } catch (err) { L = 0; }
        const at = t + k * stagger;
        if (stroked && !dashed && L > 0) {
          const len = Math.ceil(L) + 2;               // measured once, at build
          gsap.set(s, { strokeDasharray: len + " " + len, strokeDashoffset: len });
          tl.fromTo(s, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: 0.5, ease: "power2.inOut", immediateRender: false }, at);
        } else {
          const o = parseFloat(cs.opacity) || 1;
          gsap.set(s, { opacity: 0 });
          tl.fromTo(s, { opacity: 0 }, { opacity: o, duration: 0.3, ease: "power1.out", immediateRender: false }, at);
        }
      });
    },
    hide(e) {
      gsap.set(e, { opacity: 0 });
    },
  };

  // stamp target: the deepest element whose text is the number, else the number's text wrapped in a span
  const stampTarget = (e, txt) => {
    const want = (txt || "").replace(/\s+/g, " ").trim();
    if (!want) return e;
    let best = null;
    e.querySelectorAll("*").forEach((d) => {
      if ((d.textContent || "").replace(/\s+/g, " ").trim() === want) best = d;
    });
    if ((e.textContent || "").replace(/\s+/g, " ").trim() === want && !best) return e;
    if (best) {
      if (getComputedStyle(best).display === "inline") gsap.set(best, { display: "inline-block" });
      return best;
    }
    const tw = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = tw.nextNode())) {
      const i = node.textContent.indexOf(want);
      if (i < 0) continue;
      const after = node.splitText(i);
      after.splitText(want.length);
      const sp = document.createElement("span");
      sp.style.display = "inline-block";
      after.parentNode.insertBefore(sp, after);
      sp.appendChild(after);
      return sp;
    }
    return e;
  };

  const NOTE_CSS = {
    hand: "font-family:'Instrument Serif',serif;font-style:italic;font-weight:700;line-height:1.05;color:{c};white-space:pre;transform-origin:0 100%",
    sticker: "font-family:'Inter',sans-serif;font-weight:700;line-height:1;letter-spacing:-0.02em;color:#1F2937;background:{c};padding:0.32em 0.5em 0.28em;border-radius:0.22em;box-shadow:0 10px 24px rgba(0,0,0,0.14);white-space:pre;transform-origin:50% 50%",
    tag: "font-family:'JetBrains Mono',monospace;font-weight:600;line-height:1;letter-spacing:0.08em;text-transform:uppercase;color:#1F2937;background:{c};padding:0.45em 0.8em 0.4em;border-radius:999px;white-space:pre;transform-origin:50% 50%",
    mono: "font-family:'JetBrains Mono',monospace;font-weight:500;line-height:1.3;color:{c};white-space:pre;transform-origin:0 50%",
    stamp: "font-family:'Inter',sans-serif;font-weight:700;line-height:1;letter-spacing:0.04em;text-transform:uppercase;color:{c};border:0.09em solid {c};padding:0.18em 0.3em 0.12em;border-radius:0.12em;white-space:pre;transform-origin:50% 50%",
  };
  const NOTE_COLOR = { hand: "#2563EB", sticker: "#DBEAFE", tag: "#CDEFC4", mono: "#1F2937", stamp: "#E8552B" };
  const NOTE_ROT = { hand: -2.5, sticker: -4, stamp: -4, tag: 0, mono: 0 };

  const makeNote = (c) => {
    const st = NOTE_CSS[c.style] ? c.style : "hand";
    const el = document.createElement("div");
    el.className = "bs-note bs-note-" + st;
    el.setAttribute("data-u", c.id);
    el.style.cssText = "position:absolute;left:" + Math.round(c.x) + "px;top:" + Math.round(c.y) + "px;font-size:" +
      Math.round(c.size || 54) + "px;z-index:50;" + NOTE_CSS[st].split("{c}").join(c.color || NOTE_COLOR[st]);
    el.textContent = String(c.text || "").split("\\n").join("\n");
    root.appendChild(el);
    gsap.set(el, { rotation: typeof c.rot === "number" ? c.rot : NOTE_ROT[st], opacity: 0 });
    BASE.set(el, 1);
    return el;
  };

  // ── build the timeline from the cues ──
  const cues = (D.cues || []).slice().sort((a, b) => (a.t || 0) - (b.t || 0));
  cues.forEach((c) => {
    const t = AT(c.t);
    if (c.move === "note") {
      const el = makeNote(c);
      const st = NOTE_CSS[c.style] ? c.style : "hand";
      if (st === "hand") M.write(el, t, (c.size || 54) > 60 ? 0.6 : 0.45);
      else if (st === "mono") M.wipe(el, t, 0.35);
      else M.pop(el, t, 0.6);
      if (typeof c.until === "number" && c.until < D.dur - 0.05) {
        tl.to(el, { opacity: 0, duration: 0.2, ease: "power1.in" }, Math.max(t + 0.8, c.until));
      }
      return;
    }
    const e = EL[c.id];
    if (!e) return;
    switch (c.move) {
      case "label": break;                                   // on screen from the first frame
      case "hide": M.hide(e); break;
      case "rise": M.rise(e, t); break;
      case "wipe": M.wipe(e, t); break;
      case "grow": M.grow(e, t); break;
      case "growx": M.growx(e, t); break;
      case "pop": M.pop(e, t); break;
      case "write": M.write(e, t); break;
      case "draw": M.draw(e, t); break;
      case "stamp": {
        const tg = stampTarget(e, c.target);
        const fs = parseFloat(getComputedStyle(tg).fontSize) || 40;
        const big = fs > 70;
        const Z = big ? 1.22 : 1.5;
        const r0 = Number(gsap.getProperty(tg, "rotation")) || 0;
        gsap.set(tg, { transformOrigin: "50% 50%" });
        tl.fromTo(tg, { scale: 1, rotation: r0 }, { scale: Z, rotation: r0 + (big ? -1.5 : -3), duration: 0.18, ease: "power2.out", immediateRender: false }, t);
        tl.to(tg, { scale: 1, rotation: r0, duration: 0.45, ease: "back.out(1.7)" }, t + 0.18);
        break;
      }
      case "highlight": {
        const sp = byPath(c.path);
        if (!sp || sp.getClientRects().length !== 1) break;
        // the marker span stays inline (its band is painted on the inline box); an inline-block wrapper carries the pop
        const wrap = document.createElement("span");
        wrap.className = "bs-hl";
        wrap.style.display = "inline-block";
        sp.parentNode.insertBefore(wrap, sp);
        wrap.appendChild(sp);
        gsap.set(wrap, { transformOrigin: "50% 60%" });
        tl.fromTo(wrap, { scale: 1, rotation: 0 }, { scale: 1.07, rotation: -1.2, duration: 0.12, ease: "power2.out", immediateRender: false }, t);
        tl.to(wrap, { scale: 1, rotation: 0, duration: 0.3, ease: "back.out(2)" }, t + 0.12);
        break;
      }
      default: M.rise(e, t);
    }
  });
  // the timeline spans the whole board even when the last landing is early
  tl.set({}, {}, Math.max(0, D.dur || 0));
  tl.seek(0, false);

  // ── seeking ──
  const syncVideos = (t) => Promise.all(videos.map((v) => new Promise((res) => {
    const d = v.duration;
    const target = d && isFinite(d) && d > 0 ? t % d : 0;
    if (Math.abs((v.currentTime || 0) - target) < 0.0005 || v.readyState < 1) return res();
    let done = false;
    const fin = () => { if (!done) { done = true; res(); } };
    v.addEventListener("seeked", fin, { once: true });
    setTimeout(fin, 3000);
    try { v.currentTime = target; } catch (e) { fin(); }
  })));

  window.__tl = tl;
  window.__dur = D.dur;
  window.__seek = async (t) => {
    tl.seek(Math.max(0, Number(t) || 0), false);
    if (videos.length) await syncVideos(Number(t) || 0);
    await document.fonts.ready;
    return true;
  };
  window.__ready = (async () => {
    // every face the board declares (the notes use Instrument Serif / Inter / JetBrains Mono even when the board does not)
    try { await Promise.all(Array.from(document.fonts).map((f) => f.load().catch(() => null))); } catch (e) {}
    await document.fonts.ready;
    await Promise.all(Array.from(document.images).map((img) => (img.complete ? (img.decode ? img.decode().catch(() => null) : null)
      : new Promise((r) => { img.addEventListener("load", r, { once: true }); img.addEventListener("error", r, { once: true }); }))));
    await Promise.all(videos.map((v) => (v.readyState >= 2 ? null : new Promise((r) => {
      v.addEventListener("loadeddata", r, { once: true });
      v.addEventListener("error", r, { once: true });
      setTimeout(r, 8000);
    }))));
    tl.seek(0, false);
    return true;
  })();
})();
