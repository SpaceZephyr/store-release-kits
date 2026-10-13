/* product-promo-video 运行时
 * 输入: window.PV = { W, H, fps, brand, style, scenes:[{type, ..., start, dur, voice:{start,dur,text,cues}}], captions }
 * 输出: window.DURATION 和 window.seek(t) —— 画面完全由 t 决定，渲染器逐帧调 seek 截图。
 * 风格: window.STYLES[name] = { tokens, text, image, card, transitions, bg(), mark?, ghost?, sceneHook? }
 * 预览: 直接用浏览器打开 index.html 会自动播放（带 ?t=3.2 停在第 3.2 秒）。
 *
 * 每一场分两层：.scene-wrap 管转场（淡入、推走、遮罩），.scene 管镜头（推、拉、横移、快推）。
 * 镜头和元素入场都尽量挂在旁白上：念到「电话」时电话那张卡落下，念到数字时数字砸下来。
 */
(() => {
  // ---------- 缓动与工具 ----------
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const lerp = (a, b, p) => a + (b - a) * p;
  // 弹簧：bounce 0 不回弹，.15 利落，.3 明显弹（SwiftUI 的 duration/bounce 参数化）
  const spring = (bounce = .15) => x => {
    if (x >= 1) return 1;
    const z = 1 - bounce, w = 2 * Math.PI * 1.1, t = x;
    if (z >= 1) return 1 - Math.exp(-w * t) * (1 + w * t);
    const wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + z * w / wd * Math.sin(wd * t));
  };
  const E = {
    lin: x => x,
    out3: x => 1 - Math.pow(1 - x, 3),
    out5: x => 1 - Math.pow(1 - x, 5),
    in3: x => x * x * x,
    io3: x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2,
    sine: x => -(Math.cos(Math.PI * x) - 1) / 2,
    expo: x => x === 1 ? 1 : 1 - Math.pow(2, -10 * x),
    ioExpo: x => x <= 0 ? 0 : x >= 1 ? 1 : x < .5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2,
    back: x => { const c = 1.9; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); },
    spring: spring(.15), bouncy: spring(.32), soft: spring(0),
    step: n => x => Math.floor(x * n) / n,
  };
  // 确定性伪随机（同一个 seed 每帧一样）
  const rand = s => { const x = Math.sin(s * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  const seg = (t, s, d) => clamp((t - s) / d);
  window.PVU = { clamp, lerp, E, rand, seg, spring };

  const P = window.PV, S = window.STYLES[P.style];
  if (!S) throw new Error("未知风格 " + P.style);
  const T = S.tokens, root = document.documentElement, LAND = P.W >= P.H;
  // 品牌色覆盖风格默认色
  const tok = Object.assign({}, T, P.brand.colors || {}, P.tokens || {});
  for (const [k, v] of Object.entries(tok)) if (typeof v === "string") root.style.setProperty("--" + k, v);
  root.style.setProperty("--W", P.W + "px"); root.style.setProperty("--H", P.H + "px");
  document.body.className = `st-${P.style} ${LAND ? "land" : "port"}` + (S.mark ? " mark-" + S.mark : "");

  const stage = document.getElementById("stage");
  const h = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = s => String(s ?? "").replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  // **重点** → <em>；\n → 换行
  const rich = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<em>$1</em>").replace(/\n/g, "<br>");
  const plain = s => String(s ?? "").replace(/\*\*/g, "").replace(/\n/g, "");

  // ---------- 动画注册 ----------
  // 每个动画单元: {el, scene, at(场景内秒), dur, fn(el,p,lt,extra)}
  const anims = [];
  const addAnim = (scene, el, at, dur, fn, extra = {}) => anims.push({ scene, el, at, dur, fn, extra });

  // 旁白对位：某个词在这一场旁白里第几秒被念到（按字数估算，标点算停顿）。找不到返回 fallback
  const PUNCT = /[，。！？；：、,.!?;:\s]/;
  function beat(d, needle, fallback) {
    const v = d.voice; if (!v || !v.text || !needle) return fallback;
    const idx = v.text.indexOf(plain(needle)); if (idx < 0) return fallback;
    const w = ch => PUNCT.test(ch) ? 1.6 : /[A-Za-z0-9]/.test(ch) ? .45 : 1;
    let a = 0, tot = 0;
    for (let i = 0; i < v.text.length; i++) { const x = w(v.text[i]); if (i < idx) a += x; tot += x; }
    return (v.start - d.start) + v.dur * a / tot;
  }
  // 旁白里第 k/n 处（没有能对上的词时，把几样东西均匀摆在旁白上）
  const voiceAt = (d, f, fallback) => d.voice ? (d.voice.start - d.start) + d.voice.dur * f : fallback;

  // 把文字拆成字（保留 <em>/<br>），用于逐字动画
  function splitChars(el) {
    const out = [];
    const walk = (node, inEm) => {
      [...node.childNodes].forEach(n => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          for (const ch of n.textContent) {
            const sp = h("span", "ch" + (inEm ? " ch-em" : ""), ch === " " ? "&nbsp;" : esc(ch));
            frag.appendChild(sp); out.push(sp);
          }
          n.replaceWith(frag);
        } else if (n.nodeName === "EM") walk(n, true);
        else if (n.nodeName !== "BR") walk(n, inEm);
      });
    };
    walk(el, false);
    return out;
  }
  // 按 <br> 拆行，每行包一层遮罩（maskUp 用）
  function splitLines(el) {
    const parts = el.innerHTML.split(/<br\s*\/?>/);
    el.innerHTML = parts.map(p => `<span class="line"><span class="line-in">${p}</span></span>`).join("");
    return [...el.querySelectorAll(".line-in")];
  }

  // ---------- 文字入场预设 ----------
  const TEXT = {
    fadeUp(sc, el, at, o = {}) {
      addAnim(sc, el, at, o.dur || .7, (el, p) => { const e = E.out3(p); el.style.opacity = e; el.style.transform = `translateY(${(1 - e) * (o.dist || 40)}px)`; });
    },
    blurIn(sc, el, at, o = {}) {
      addAnim(sc, el, at, o.dur || 1.1, (el, p) => { const e = E.out3(p); el.style.opacity = e; el.style.filter = `blur(${(1 - e) * 18}px)`; el.style.transform = `scale(${lerp(1.08, 1, e)})`; });
    },
    letterSpace(sc, el, at, o = {}) { // 字距收拢（发布会/奢侈品常见）
      addAnim(sc, el, at, o.dur || 1.4, (el, p) => { const e = E.out5(p); el.style.opacity = E.out3(clamp(p * 1.6)); el.style.letterSpacing = `${(1 - e) * .5}em`; el.style.filter = `blur(${(1 - e) * 6}px)`; });
    },
    charStagger(sc, el, at, o = {}) {
      const chs = splitChars(el), gap = o.gap ?? Math.min(.05, 1 / Math.max(chs.length, 1));
      chs.forEach((c, i) => addAnim(sc, c, at + i * gap, o.dur || .6, (c, p) => { const e = E.out3(p); c.style.opacity = e; c.style.transform = `translateY(${(1 - e) * 0.6}em)`; }));
    },
    // 逐字立起来：绕 X 轴从 -90° 翻上来，弹簧落定（发布会、SaaS 常见）
    rise3d(sc, el, at, o = {}) {
      const chs = splitChars(el), gap = o.gap ?? Math.min(.045, .9 / Math.max(chs.length, 1));
      el.style.perspective = "900px";
      chs.forEach((c, i) => addAnim(sc, c, at + i * gap, o.dur || .9, (c, p) => {
        const e = E.spring(p); c.style.opacity = clamp(p * 3);
        c.style.transform = `translateY(${(1 - e) * .5}em) rotateX(${(1 - e) * -95}deg)`; c.style.transformOrigin = "50% 100% -20px";
        c.style.filter = `blur(${(1 - clamp(p * 2)) * 6}px)`;
      }));
    },
    // 逐字从大砸到小，带一点旋转（快节奏）
    charSlam(sc, el, at, o = {}) {
      const chs = splitChars(el), gap = o.gap ?? Math.min(.04, .7 / Math.max(chs.length, 1));
      chs.forEach((c, i) => addAnim(sc, c, at + i * gap, o.dur || .5, (c, p) => {
        const e = E.bouncy(p); c.style.opacity = clamp(p * 6);
        c.style.transform = `scale(${lerp(2.6, 1, e)}) rotate(${(1 - e) * (i % 2 ? 9 : -9)}deg)`;
      }));
    },
    charPop(sc, el, at, o = {}) { // 逐字弹出（MG/卡通）
      const chs = splitChars(el), gap = o.gap ?? Math.min(.06, 1.2 / Math.max(chs.length, 1));
      chs.forEach((c, i) => addAnim(sc, c, at + i * gap, o.dur || .55, (c, p) => { c.style.opacity = clamp(p * 4); c.style.transform = `translateY(${(1 - E.out3(p)) * .5}em) scale(${E.back(p)}) rotate(${(1 - E.out3(p)) * (i % 2 ? 14 : -14)}deg)`; }));
    },
    maskUp(sc, el, at, o = {}) { // 行遮罩上推（编辑/高级感）
      const lines = splitLines(el);
      lines.forEach((l, i) => addAnim(sc, l, at + i * (o.gap || .12), o.dur || .9, (l, p) => { const e = E.out5(p); l.style.transform = `translateY(${(1 - e) * 110}%) skewY(${(1 - e) * 6}deg)`; }));
    },
    punch(sc, el, at, o = {}) { // 大字砸入（快节奏）：1.55 → 0.94 → 1
      addAnim(sc, el, at, o.dur || .5, (el, p, lt) => {
        el.style.opacity = clamp(p * 6);
        const s = p < .35 ? lerp(o.from || 2.2, .94, E.out3(p / .35)) : lerp(.94, 1, E.out3((p - .35) / .65));
        el.style.transform = `scale(${s})`;
        el.style.filter = `blur(${(1 - clamp(p * 3)) * 10}px)`;
      });
    },
    typewriter(sc, el, at, o = {}) {
      const chs = splitChars(el), cps = o.cps || 16;
      const caret = h("span", "caret", "▍"); el.appendChild(caret);
      addAnim(sc, el, at, chs.length / cps + 1.5, (el, p, lt) => {
        const n = Math.floor(lt * cps); chs.forEach((c, i) => c.style.opacity = i < n ? 1 : 0);
        caret.style.opacity = (Math.floor(lt * 2.2) % 2 === 0 || n < chs.length) ? 1 : 0;
      });
    },
    glitch(sc, el, at, o = {}) { // 乱码解码 + RGB 分离
      const chs = splitChars(el), pool = "▓▒░#@$%&*01ABCDEFXYZ<>/\\";
      const orig = chs.map(c => c.textContent);
      addAnim(sc, el, at, o.dur || .8, (el, p, lt) => {
        const f = Math.floor(lt * 30);
        chs.forEach((c, i) => {
          const done = p >= (i + 1) / (chs.length + 2) * .8;
          c.textContent = done ? orig[i] : pool[Math.floor(rand(f * 31 + i) * pool.length)];
          c.style.opacity = p > i / chs.length * .4 ? 1 : 0;
        });
        const k = (1 - p) * 10 + (p < 1 && rand(f) > .9 ? 6 : 0);
        el.style.textShadow = `${k}px 0 var(--glitchA, #ff004c), ${-k}px 0 var(--glitchB, #00e5ff)`;
        el.style.transform = `translateX(${p < 1 && rand(f + 7) > .85 ? (rand(f) - .5) * 30 : 0}px)`;
      });
    },
    slideHard(sc, el, at, o = {}) { // 硬切滑入（新粗野）
      addAnim(sc, el, at, o.dur || .35, (el, p) => { const e = E.step(5)(p); el.style.opacity = p > 0 ? 1 : 0; el.style.transform = `translateX(${(1 - e) * -120}px) rotate(${(1 - e) * -3}deg)`; });
    },
    none(sc, el, at) { addAnim(sc, el, at, .01, (el, p) => el.style.opacity = p > 0 ? 1 : 0); },
  };

  // ---------- 图片 / 媒体入场预设 ----------
  const IMAGE = {
    floatUp(sc, el, at, o = {}) {
      addAnim(sc, el, at, o.dur || 1.0, (el, p) => { const e = E.spring(p); el.style.opacity = clamp(p * 3); el.style.transform = `translateY(${(1 - e) * 160}px) scale(${lerp(.92, 1, e)})`; });
    },
    // 从下方带透视立起来、弹簧落平（产品发布片最常见的截图入场）
    swing3d(sc, el, at, o = {}) {
      addAnim(sc, el, at, o.dur || 1.3, (el, p) => {
        const e = E.spring(p); el.style.opacity = clamp(p * 4);
        el.style.transform = `perspective(2000px) translateY(${(1 - e) * 320}px) rotateX(${(1 - e) * 52}deg) rotateZ(${(1 - e) * (o.dir || 1) * -6}deg) scale(${lerp(.82, 1, e)})`;
      });
    },
    tilt3d(sc, el, at, o = {}) { // 透视立起来，停在一个斜角上（SaaS 发布会常见）
      addAnim(sc, el, at, o.dur || 1.4, (el, p, lt) => { const e = E.spring(p); el.style.opacity = clamp(p * 2.5); el.style.transform = `perspective(1800px) rotateX(${lerp(42, 8, e)}deg) rotateY(${lerp(-24, -6, e) * (o.dir || 1)}deg) translateY(${(1 - e) * 220}px) scale(${lerp(.82, 1, e)})`; });
    },
    zoomOut(sc, el, at, o = {}) {
      addAnim(sc, el, at, o.dur || 1.0, (el, p) => { const e = E.spring(p); el.style.opacity = clamp(p * 3); el.style.filter = `blur(${(1 - clamp(p * 1.6)) * 14}px)`; el.style.transform = `scale(${lerp(1.3, 1, e)})`; });
    },
    popBounce(sc, el, at, o = {}) {
      addAnim(sc, el, at, o.dur || .8, (el, p) => { el.style.opacity = clamp(p * 4); el.style.transform = `scale(${E.back(p)}) rotate(${(1 - E.out3(p)) * -8}deg)`; });
    },
    // 卡片从景深里翻过来（3D 发牌）
    flip3d(sc, el, at, o = {}) {
      addAnim(sc, el, at, o.dur || .9, (el, p) => {
        const e = E.spring(p); el.style.opacity = clamp(p * 3);
        el.style.transform = `perspective(1400px) translateZ(${(1 - e) * -500}px) translateY(${(1 - e) * 120}px) rotateY(${(1 - e) * 70}deg) rotateX(${(1 - e) * 20}deg)`;
      });
    },
    wipe(sc, el, at, o = {}) {
      addAnim(sc, el, at, o.dur || .9, (el, p) => { const e = E.io3(p); el.style.opacity = 1; el.style.clipPath = `inset(0 ${(1 - e) * 100}% 0 0)`; el.style.transform = `scale(${1.06 - e * .06})`; });
    },
    glitch(sc, el, at, o = {}) {
      addAnim(sc, el, at, o.dur || .8, (el, p, lt) => {
        const f = Math.floor(lt * 30), on = p < 1 && rand(f) > .4;
        el.style.opacity = p > 0 ? 1 : 0;
        el.style.clipPath = on ? `inset(${rand(f + 1) * 60}% 0 ${rand(f + 2) * 30}% 0)` : "none";
        el.style.transform = `translateX(${on ? (rand(f + 3) - .5) * 60 : 0}px) scale(${on ? 1.03 : 1})`;
        el.style.filter = on ? `hue-rotate(${rand(f) * 180}deg) saturate(2)` : "none";
      });
    },
    slideHard(sc, el, at, o = {}) {
      addAnim(sc, el, at, o.dur || .4, (el, p) => { const e = E.step(6)(p); el.style.opacity = p > 0 ? 1 : 0; el.style.transform = `translate(${(1 - e) * 220 * (o.dir || 1)}px, ${(1 - e) * -40}px) rotate(${(1 - e) * 4}deg)`; });
    },
  };

  // ---------- 转场预设（out = 上一场，in = 下一场，p 0..1） ----------
  const fx = document.getElementById("fx");
  const W = P.W, H = P.H;
  const TRANS = {
    cut(o, i, p) { o.style.opacity = p < .5 ? 1 : 0; i.style.opacity = p < .5 ? 0 : 1; },
    fade(o, i, p) { o.style.opacity = 1 - p; i.style.opacity = p; },
    blur(o, i, p) { const e = E.io3(p); o.style.opacity = 1 - e; o.style.filter = `blur(${e * 24}px)`; i.style.opacity = e; i.style.filter = `blur(${(1 - e) * 24}px)`; },
    // 旧画面缩小模糊退后，新画面从稍大处落定（发布会）
    blurPush(o, i, p) {
      const e = E.io3(p);
      o.style.opacity = 1 - E.in3(p); o.style.filter = `blur(${e * 26}px)`; o.style.transform = `scale(${lerp(1, .9, e)})`;
      i.style.opacity = E.out3(p); i.style.filter = `blur(${(1 - e) * 22}px)`; i.style.transform = `scale(${lerp(1.12, 1, E.out5(p))})`;
    },
    // 镜头冲进旧画面中心，新画面从景深里出来
    zoomThrough(o, i, p) {
      const a = E.in3(clamp(p / .55)), b = E.out5(clamp((p - .4) / .6));
      o.style.transform = `scale(${1 + a * 2.2})`; o.style.filter = `blur(${a * 18}px)`; o.style.opacity = 1 - clamp((p - .35) / .25);
      i.style.opacity = clamp((p - .4) / .2); i.style.transform = `scale(${lerp(.55, 1, b)})`; i.style.filter = `blur(${(1 - b) * 16}px)`;
    },
    // 甩镜：横向快速甩走，中间带运动模糊
    whip(o, i, p) {
      const e = E.ioExpo(p), v = Math.sin(Math.PI * p);
      o.style.transform = `translateX(${-e * W * 1.1}px) skewX(${v * 6}deg)`; o.style.filter = `blur(${v * 28}px)`; o.style.opacity = 1;
      i.style.transform = `translateX(${(1 - e) * W * 1.1}px) skewX(${v * 6}deg)`; i.style.filter = `blur(${v * 28}px)`; i.style.opacity = 1;
    },
    whipUp(o, i, p) {
      const e = E.ioExpo(p), v = Math.sin(Math.PI * p);
      o.style.transform = `translateY(${-e * H * 1.1}px)`; o.style.filter = `blur(${v * 24}px)`;
      i.style.transform = `translateY(${(1 - e) * H * 1.1}px)`; i.style.filter = `blur(${v * 24}px)`; i.style.opacity = 1;
    },
    push(o, i, p) { const e = E.io3(p); o.style.transform = `translateX(${-e * 100}%)`; i.style.transform = `translateX(${(1 - e) * 100}%)`; i.style.opacity = 1; },
    pushUp(o, i, p) { const e = E.io3(p); o.style.transform = `translateY(${-e * 40}%) scale(${lerp(1, .94, e)})`; o.style.opacity = 1 - e * .6; i.style.transform = `translateY(${(1 - e) * 100}%)`; i.style.opacity = 1; },
    zoom(o, i, p) { const e = E.io3(p); o.style.transform = `scale(${1 + e * .6})`; o.style.opacity = 1 - e; i.style.transform = `scale(${lerp(.75, 1, e)})`; i.style.opacity = e; },
    circle(o, i, p) { const e = E.io3(p); i.style.opacity = 1; i.style.clipPath = `circle(${e * 75}% at 50% 50%)`; o.style.transform = `scale(${1 + e * .15})`; },
    // 竖条从下往上依次长出来，露出新画面
    bars(o, i, p) {
      const n = 7, pts = ["0% 100%"];
      for (let k = 0; k < n; k++) {
        const hh = E.io3(clamp(p * 1.7 - k * .1)) * 100, x0 = k / n * 100, x1 = (k + 1) / n * 100 + .2;
        pts.push(`${x0}% ${100 - hh}%`, `${x1}% ${100 - hh}%`);
      }
      pts.push("100% 100%");
      i.style.opacity = 1; i.style.clipPath = `polygon(${pts.join(",")})`; o.style.transform = `translateY(${-E.in3(p) * 6}%)`;
    },
    // 品牌色色块扫过（MG / 扁平风）
    shapeWipe(o, i, p) {
      const e = E.io3(p);
      fx.style.display = "block"; fx.className = "fx-wipe";
      fx.style.transform = `translateX(${lerp(-110, 110, e)}%) skewX(-12deg)`;
      o.style.opacity = e < .5 ? 1 : 0; i.style.opacity = e < .5 ? 0 : 1;
      i.style.transform = `scale(${lerp(1.08, 1, E.out3(clamp((p - .5) * 2)))})`;
    },
    spin(o, i, p) {
      const e = E.ioExpo(p), v = Math.sin(Math.PI * p);
      o.style.transform = `rotate(${-e * 14}deg) scale(${1 + e * .5})`; o.style.opacity = 1 - clamp((p - .4) / .2); o.style.filter = `blur(${v * 14}px)`;
      i.style.transform = `rotate(${(1 - e) * 14}deg) scale(${lerp(1.5, 1, e)})`; i.style.opacity = clamp((p - .4) / .2); i.style.filter = `blur(${v * 14}px)`;
    },
    flash(o, i, p) { fx.style.display = "block"; fx.className = "fx-flash"; fx.style.opacity = 1 - Math.abs(p - .5) * 2; o.style.opacity = p < .5 ? 1 : 0; i.style.opacity = p < .5 ? 0 : 1; i.style.transform = `scale(${lerp(1.15, 1, E.out3(clamp((p - .5) * 2)))})`; },
    glitchCut(o, i, p) {
      const f = Math.floor(p * 12), a = p < .5 ? o : i, b = p < .5 ? i : o;
      a.style.opacity = 1; b.style.opacity = 0;
      a.style.transform = `translateX(${(rand(f) - .5) * 80}px)`;
      a.style.clipPath = `inset(${rand(f + 1) * 40}% 0 ${rand(f + 2) * 40}% 0)`;
      a.style.filter = `hue-rotate(${rand(f + 3) * 90}deg)`;
      fx.style.display = "block"; fx.className = "fx-scan"; fx.style.opacity = 1 - Math.abs(p - .5) * 2;
    },
    stripes(o, i, p) { // 多条色带依次扫过
      fx.style.display = "block"; fx.className = "fx-stripes";
      [...fx.children].forEach((c, k) => { const e = E.io3(clamp(p * 1.6 - k * .12)); c.style.transform = `translateX(${lerp(-105, 105, e)}%)`; });
      o.style.opacity = p < .5 ? 1 : 0; i.style.opacity = p < .5 ? 0 : 1;
    },
  };
  // 色带元素
  for (let k = 0; k < 4; k++) fx.appendChild(h("i"));

  window.PV_TEXT = TEXT; window.PV_IMAGE = IMAGE; window.PV_TRANS = TRANS;

  // ---------- 镜头 ----------
  // 每场一份镜头表：init 起始机位，moves 依次执行（at 场景内秒、dur、to 目标、ease）。
  // 动作：推(s 变大)、拉(s 变小)、横移(x/y)、快推(短 dur)、慢漂(长 dur + lin)。
  const camOf = sc => sc.cam || (sc.cam = { init: { x: 0, y: 0, s: 1, r: 0 }, moves: [] });
  const camInit = (sc, v) => Object.assign(camOf(sc).init, v);
  const camMove = (sc, at, dur, to, ease = E.io3) => camOf(sc).moves.push({ at, dur, to, ease });
  function camAt(sc, lt) {
    const c = camOf(sc); let cur = { ...c.init };
    for (const m of c.moves) {
      if (lt <= m.at) break;
      const tgt = { ...cur, ...m.to };
      if (lt >= m.at + m.dur) { cur = tgt; continue; }
      const e = m.ease(clamp((lt - m.at) / m.dur));
      for (const k in tgt) cur[k] = lerp(cur[k], tgt[k], e);
      break;
    }
    return cur;
  }
  // 慢漂：落定之后画面也一直有点动，方向每场不同
  const drift = (sc, from, k = 1) => {
    const dir = sc.idx % 4, end = sc.dur;
    const to = [{ s: 1.035 }, { x: -18, s: 1.02 }, { y: -14, s: 1.025 }, { x: 16, s: 1.02 }][dir];
    const base = camAt(sc, from);
    camMove(sc, from, Math.max(end - from, .5), Object.fromEntries(Object.entries(to).map(([key, v]) => [key, key === "s" ? base.s * (1 + (v - 1) * k) : base[key] + v * k])), E.lin);
  };

  // ---------- 场景元素 ----------
  let logoN = 0;
  const logoEl = (cls = "logo") => {
    const b = P.brand, w = h("div", cls), n = ++logoN;
    // 同一个 SVG 插两次时 id 会重复，前一个被隐藏后后一个的渐变/裁切引用就失效，所以每份加后缀
    if (b.logoSvg) w.innerHTML = b.logoSvg.replace(/\bid="([^"]+)"/g, `id="$1-${n}"`).replace(/url\(#([^)]+)\)/g, `url(#$1-${n})`).replace(/href="#([^"]+)"/g, `href="#$1-${n}"`); else if (b.logo) { const im = h("img"); im.src = b.logo; w.appendChild(im); }
    else w.appendChild(h("div", "logo-text", esc(b.name)));
    // 一道光扫过 logo（遮罩成 logo 的形状，只亮在 logo 上）
    const src = b.logoSvg ? "data:image/svg+xml;charset=utf-8," + encodeURIComponent(b.logoSvg) : b.logo;
    if (src) { const sh = h("i", "sheen"); sh.style.webkitMaskImage = sh.style.maskImage = `url("${src}")`; w.appendChild(sh); }
    return w;
  };
  const sheen = (sc, logo, at) => { const sh = logo.querySelector(".sheen"); if (sh) addAnim(sc, sh, at, .9, (el, p) => { el.style.opacity = 1; el.style.backgroundPosition = `${lerp(130, -30, E.io3(p))}% 0`; }); };
  // 冲击波：从一点扩散的圆环（logo 落下、数字砸下时用）
  const rings = (sc, host, at, n = 2, o = {}) => {
    for (let k = 0; k < n; k++) {
      const r = h("i", "ring"); if (o.x != null) { r.style.left = o.x; r.style.top = o.y; } host.appendChild(r);
      addAnim(sc, r, at + k * .14, o.dur || 1.1, (el, p) => { const e = E.out3(p); el.style.opacity = (1 - p) * (o.alpha || .7); el.style.transform = `translate(-50%,-50%) scale(${lerp(.2, o.size || 2.4, e)})`; });
    }
  };
  // 背景大字：一行巨大的描边字缓慢横移（让画面一直有东西在动）
  const ghost = (sc, el, text, dir = 1) => {
    if (S.ghost === false || !text) return;
    const g = h("div", "ghost", esc(plain(text) + "  ·  ").repeat(4)); el.prepend(g);
    addAnim(sc, g, 0, sc.dur, (g, p, lt) => { g.style.opacity = clamp(lt * 2) * 1; g.style.transform = `translateY(-50%) translateX(${-W * .3 - dir * lt * 70}px)`; });
  };
  // 重点词底下划一道色带
  const mark = (sc, box, at) => {
    if (!S.mark) return;
    box.querySelectorAll(".title em").forEach((em, k) => addAnim(sc, em, at + k * .15, .55, (el, p) => { el.style.setProperty("--mk", (E.out3(p) * 100) + "%"); }, { keep: true }));
  };
  const textBlock = (sc, d, cls = "copy") => {
    const box = h("div", cls);
    if (d.kicker) box.appendChild(h("div", "kicker", rich(d.kicker)));
    if (d.title) box.appendChild(h("div", "title", rich(d.title)));
    if (d.sub) box.appendChild(h("div", "sub", rich(d.sub)));
    return box;
  };
  function animCopy(sc, box, at) {
    const k = box.querySelector(".kicker"), t = box.querySelector(".title"), s = box.querySelector(".sub");
    let a = at;
    if (k) { S.text.kicker(sc, k, a); a += .2; }
    if (t) { S.text.title(sc, t, a); mark(sc, box, a + .55); a += .4; }
    if (s) S.text.sub(sc, s, a + .15);
  }

  // 截图：按图片真实比例算出显示框，再算放大镜要截哪一块
  const SPEC = {
    browser: { bar: 44, ar: 1.6 },
    phone: { bar: 0 },
    none: { bar: 0 },
  };
  function media(sc, d, width, maxH) {
    const frame = d.frame || (LAND ? "browser" : "phone");
    const wrap = h("div", "mwrap"), m = h("div", "media frame-" + frame); wrap.appendChild(m);
    if (frame === "browser") m.appendChild(h("div", "bar", "<i></i><i></i><i></i><span></span>"));
    if (frame === "phone") m.appendChild(h("div", "notch"));
    const box = h("div", "screen"), img = h("img"); img.src = d.image; box.appendChild(img); m.appendChild(box);
    const AR = d.imageAR || 1.6;
    let Wb, Hb;
    if (frame === "phone") { Hb = (LAND ? 860 : 1100) - 32; Wb = Hb * 9 / 19.5; }
    else { Wb = width; Hb = frame === "browser" ? Wb / 1.6 : Math.min(Wb / AR, maxH); if (frame !== "browser" && Wb / AR > maxH) { Wb = Math.min(Wb, maxH * AR); Hb = Wb / AR; } }
    if (frame !== "phone") { m.style.width = Wb + "px"; box.style.height = Hb + "px"; }
    wrap.style.width = (frame === "phone" ? Wb + 32 : Wb) + "px";
    const geo = { frame, Wb, Hb, bar: SPEC[frame].bar, pad: frame === "phone" ? 16 : 0, AR, wrap, m, box };
    return geo;
  }
  // 放大镜：把截图里 focus 那一块放大，弹到截图上方；其余部分压暗
  function lens(sc, g, d, at) {
    const [fx_, fy, z0] = d.focus, z = Math.max(z0 || 1.8, 1.4);
    const sc_ = Math.max(g.Wb / g.AR, g.Hb), dispW = g.AR * sc_, dispH = sc_, offX = (g.Wb - dispW) / 2;
    const ux = fx_ * g.Wb - offX, uy = fy * g.Hb;
    const cw = Math.min(g.Wb * .6, 720), ch = cw * .6;
    const L = h("div", "lens"); L.style.width = cw + "px"; L.style.height = ch + "px";
    L.style.backgroundImage = `url("${d.image}")`; L.style.backgroundSize = `${dispW * z}px ${dispH * z}px`;
    L.style.backgroundPosition = `${cw / 2 - ux * z}px ${ch / 2 - uy * z}px`;
    // 放大镜的落点：以 focus 为中心，往截图外侧挪一点，别整个盖住原处
    const px = g.pad + fx_ * g.Wb, py = g.pad + g.bar + fy * g.Hb;
    const lx = clamp(px + (fx_ > .5 ? -cw * .12 : cw * .12), cw * .38, g.Wb + g.pad * 2 - cw * .38), ly = clamp(py - ch * .12, ch * .3, g.Hb + g.bar + g.pad * 2 - ch * .3);
    L.style.left = (lx - cw / 2) + "px"; L.style.top = (ly - ch / 2) + "px";
    g.wrap.appendChild(L);
    const spot = h("div", "spot"); spot.style.setProperty("--fx", fx_ * 100 + "%"); spot.style.setProperty("--fy", fy * 100 + "%"); g.box.appendChild(spot);
    addAnim(sc, spot, at - .1, .6, (el, p) => { el.style.opacity = E.out3(p); }, {});
    addAnim(sc, L, at, .8, (el, p) => {
      const e = E.bouncy(p); el.style.opacity = clamp(p * 4);
      el.style.transformOrigin = `${(px - lx + cw / 2) / cw * 100}% ${(py - ly + ch / 2) / ch * 100}%`;
      el.style.transform = `scale(${lerp(.15, 1, e)}) rotate(${(1 - e) * -6}deg)`;
    });
    if (d.callout) { const c = h("div", "callout", rich(d.callout)); L.appendChild(c); TEXT.fadeUp(sc, c, at + .35, { dist: 16, dur: .5 }); }
    return { px, py };
  }

  // 每种场景：建 DOM + 安排入场 + 写镜头
  let featureN = 0;
  const LAYOUT = {
    logo(sc, d, el) {
      const lg = logoEl(); el.appendChild(lg);
      const tl = h("div", "tagline", rich(d.tagline || P.brand.slogan || "")); el.appendChild(tl);
      rings(sc, el, .35, 3, { size: LAND ? 3.2 : 2.6, alpha: .5 });
      (S.logoIn || IMAGE.popBounce)(sc, lg, .2);
      sheen(sc, lg, 1.0);
      S.text.sub(sc, tl, Math.max(.9, beat(d, d.tagline, .9) - .25));
      camInit(sc, { s: 1.22, r: -2 }); camMove(sc, 0, 1.5, { s: 1, r: 0 }, E.soft); drift(sc, 1.5, 1.2);
    },
    slogan(sc, d, el) {
      const tb = textBlock(sc, d, "copy center"); el.appendChild(tb);
      ghost(sc, el, (d.title || "").match(/\*\*(.+?)\*\*/)?.[1] || d.title, sc.idx % 2 ? 1 : -1);
      animCopy(sc, tb, .15);
      const v = sc.idx % 3;
      if (v === 0) { camInit(sc, { s: 1.14, r: 2.5 }); camMove(sc, 0, 1.2, { s: 1, r: 0 }, E.spring); }
      else if (v === 1) { camInit(sc, { x: -220, s: 1.06 }); camMove(sc, 0, 1.0, { x: 0, s: 1 }, E.out5); }
      else { camInit(sc, { y: 160, s: 1.08 }); camMove(sc, 0, 1.0, { y: 0, s: 1 }, E.spring); }
      drift(sc, 1.3);
    },
    feature(sc, d, el, idx) {
      const k = featureN++;
      const layout = d.layout || (!LAND ? "stack" : (d.frame === "phone" ? "split" : (k % 2 ? "hero" : "split")));
      el.classList.add("lay-" + layout);
      // hero 版式上方只有一行的位置，标题合成一行
      const tb = textBlock(sc, layout === "hero" ? { ...d, title: (d.title || "").replace(/\n/g, " ") } : d);
      if (d.bullets) { const ul = h("ul", "bullets"); d.bullets.forEach(b => ul.appendChild(h("li", "", rich(b)))); tb.appendChild(ul); }
      let side = d.side || (k % 2 ? "right" : "left");
      let g;
      if (layout === "hero") {
        tb.classList.add("hero-copy");
        // 截图底边停在字幕区上方（字幕在底部 64px 起，约 90px 高）
        const maxH = H - 262 - 190, fr = d.frame || "browser";
        g = media(sc, d, Math.round(Math.min(W * .66, fr === "browser" ? (maxH - 44) * 1.6 : W)), maxH);
        el.append(tb, g.wrap);
      } else if (layout === "stack") {
        g = media(sc, d, Math.round(W - 160), H * .5);
        el.append(tb, g.wrap);
      } else {
        el.classList.add("side-" + side);
        g = media(sc, d, Math.round((W - 280) * .58), H - 240);
        el.append(tb, g.wrap);
      }
      animCopy(sc, tb, .1);
      if (d.bullets) [...tb.querySelectorAll("li")].forEach((li, j) => S.text.sub(sc, li, beat(d, li.textContent, 1.0 + j * .25) - .2));
      (S.image || IMAGE.swing3d)(sc, g.m, layout === "hero" ? .45 : .3, { dir: side === "left" ? 1 : -1 });
      // 镜头：先从截图那一侧带进来，落定；念到重点时推过去看放大镜；收尾前拉回来
      const mx = layout === "split" ? (side === "left" ? 1 : -1) * W * .2 : 0;
      if (layout === "hero") { camInit(sc, { y: -120, s: 1.12 }); camMove(sc, 0, 1.3, { y: 0, s: 1 }, E.soft); }
      else { camInit(sc, { x: -mx * .5, s: 1.1, r: (side === "left" ? -1 : 1) * 1.5 }); camMove(sc, 0, 1.2, { x: 0, s: 1, r: 0 }, E.soft); }
      const fAt = d.focus ? beat(d, d.focusAt, Math.max(1.6, sc.dur * .42)) : null;
      if (d.focus) {
        // 先粗算放大镜在画面里的位置，镜头往那边推一点
        const gx = layout === "split" ? (side === "left" ? W - 140 - g.Wb : 140) : (W - g.Wb) / 2;
        const gy = layout === "hero" ? 300 : (H - g.Hb) / 2;
        const fpx = gx + d.focus[0] * g.Wb, fpy = gy + g.bar + d.focus[1] * g.Hb, k = layout === "split" ? .1 : .3;
        camMove(sc, fAt - .15, .9, { s: layout === "split" ? 1.05 : 1.14, x: -(fpx - W / 2) * k, y: -(fpy - H / 2) * k }, E.io3);
        lens(sc, g, d, fAt + .2);
        camMove(sc, Math.max(fAt + 1.4, sc.dur - 1.3), 1.0, { s: 1.03, x: 0, y: 0 }, E.io3);
      } else drift(sc, 1.3);
    },
    cards(sc, d, el) {
      const tb = textBlock(sc, d, "copy center top"); el.appendChild(tb); animCopy(sc, tb, .1);
      const g = h("div", "grid n" + d.items.length); el.appendChild(g);
      const n = d.items.length, times = d.items.map((it, k) => beat(d, it.label, null));
      const synced = times.filter(x => x != null).length >= Math.ceil(n / 2);
      d.items.forEach((it, k) => {
        const c = h("div", "card");
        if (it.image) { const im = h("div", "card-img"); im.style.backgroundImage = `url("${it.image}")`; c.appendChild(im); }
        else if (it.iconSvg) c.appendChild(h("div", "card-icon", it.iconSvg));
        else c.appendChild(h("div", "card-num", String(k + 1).padStart(2, "0")));
        c.appendChild(h("div", "card-label", rich(it.label)));
        if (it.desc) c.appendChild(h("div", "card-desc", rich(it.desc)));
        g.appendChild(c);
        // 念到这张卡时落下；对不上旁白就依次发牌
        const at = synced && times[k] != null ? Math.max(.5, times[k] - .3) : .6 + k * (S.cardGap || .14);
        (S.card || IMAGE.flip3d)(sc, c, at);
        // 图标笔画画出来
        c.querySelectorAll(".card-icon svg *").forEach(p => {
          if (!p.getTotalLength) return;
          addAnim(sc, p, at + .2, .8, (el, q) => {
            const L = el._len || (el._len = el.getTotalLength() + 1);
            if (L < 3) return;
            el.style.strokeDasharray = L; el.style.strokeDashoffset = L * (1 - E.out3(q));
          }, { keep: true });
        });
        // 被念到的这张抬起来一点，下一张念到时放下
        if (synced && times[k] != null) {
          const nxt = times.slice(k + 1).find(x => x != null) ?? (d.voice ? d.voice.start - d.start + d.voice.dur + .3 : sc.dur);
          addAnim(sc, c, at, Math.max(nxt - at, .3), (el, q, lt) => {
            const up = E.out3(clamp(lt / .3)) * (1 - E.out3(clamp((lt - (nxt - at)) / .3)));
            el.style.scale = 1 + up * .045; el.style.setProperty("--lift", up);
          }, { keep: true });
        }
      });
      const first = synced ? Math.min(...times.filter(x => x != null)) - .3 : .6;
      camInit(sc, { y: 140, s: 1.16 }); camMove(sc, Math.max(.2, first - .3), 1.2, { y: 0, s: 1 }, E.soft); drift(sc, first + 1, .7);
    },
    stats(sc, d, el) {
      const tb = textBlock(sc, d, "copy center top"); el.appendChild(tb); animCopy(sc, tb, .1);
      const g = h("div", "stats n" + d.items.length); el.appendChild(g);
      const n = d.items.length;
      camInit(sc, { s: 1.06 }); camMove(sc, 0, .8, { s: 1 }, E.out3);
      d.items.forEach((it, k) => {
        const c = h("div", "stat"), v = h("div", "stat-v"), l = h("div", "stat-l", rich(it.label)), bar = h("i", "stat-bar");
        c.append(v, bar, l); g.appendChild(c);
        const m = String(it.value).match(/^([^\d]*)([\d.]+)(.*)$/) || ["", "", it.value, ""];
        const num = parseFloat(m[2]), dec = (m[2].split(".")[1] || "").length;
        const at = Math.max(.5 + k * .2, beat(d, it.say || it.label, voiceAt(d, (k + .15) / n, .5 + k * .3)) - .15);
        // 数字砸下来：1.6 → .94 → 1，同时数上去
        addAnim(sc, v, at, 1.5, (v, p, lt) => {
          const q = clamp(lt / .5), s = q < .35 ? lerp(1.7, .94, E.out3(q / .35)) : lerp(.94, 1, E.out3((q - .35) / .65));
          v.style.opacity = clamp(lt * 8); v.style.transform = `scale(${s})`; v.style.filter = `blur(${(1 - clamp(lt * 4)) * 10}px)`;
          v.innerHTML = esc(m[1]) + (isNaN(num) ? esc(m[2]) : (num * E.expo(clamp(lt / 1.1))).toFixed(dec)) + `<small>${esc(m[3])}</small>`;
        });
        addAnim(sc, bar, at + .25, .7, (el, p) => { el.style.transform = `scaleX(${E.out5(p)})`; });
        TEXT.fadeUp(sc, l, at + .3, { dist: 20, dur: .5 });
        rings(sc, c, at + .05, 1, { x: "50%", y: "38%", size: 1.6, alpha: .45, dur: .8 });
        // 每个数字落下时镜头快推一下再回来
        camMove(sc, at + .02, .17, { s: 1.045 }, E.out3); camMove(sc, at + .19, .6, { s: 1.0 + k * .01 }, E.out3);
      });
    },
    // 标签流：danmaku(弹幕飞过) / cloud(两圈标签绕着标题转，前大后小) / marquee(整行滚动)
    tags(sc, d, el) {
      const tb = textBlock(sc, d, "copy center mid"); el.appendChild(tb); animCopy(sc, tb, .2);
      const mode = d.mode || S.tagMode || "cloud", box = h("div", "tagfield mode-" + mode); el.appendChild(box);
      const lanes = mode === "danmaku" ? (LAND ? 9 : 14) : 0;
      d.items.forEach((txt, k) => {
        const t = h("span", "tag" + (k % 3 === 0 ? " tag-a" : k % 3 === 1 ? " tag-b" : ""), rich(txt)); box.appendChild(t);
        if (mode === "danmaku") {
          // 一部分弹幕开场就已经在屏幕上，避免空屏；速度按字数略有差异，像真弹幕
          const lane = k % lanes, y = 5 + lane * (90 / lanes), v = W * (.2 + rand(k) * .12);
          const x0 = W * (rand(k + 9) * 1.6 - .2) + Math.floor(k / lanes) * W * .5;
          t.style.top = y + "%";
          addAnim(sc, t, 0, sc.dur, (t, p, lt) => { t.style.opacity = 1; t.style.transform = `translateX(${x0 - lt * v}px)`; });
        } else if (mode === "marquee") {
          t.style.top = (8 + (k % 6) * 15) + "%";
          addAnim(sc, t, 0, sc.dur, (t, p, lt) => { const dir = (k % 6) % 2 ? 1 : -1, x = (Math.floor(k / 6) * 380 + lt * 160 * dir) % (W + 400); t.style.opacity = 1; t.style.transform = `translateX(${dir > 0 ? x - 400 : W + x}px)`; });
        } else {
          // 两圈椭圆轨道，内外圈反向慢转；靠前的大而清楚，靠后的小、淡、略糊（假 3D）
          const n = d.items.length, ring = k % 2, nr = ring ? Math.floor(n / 2) : Math.ceil(n / 2), j = Math.floor(k / 2);
          const a0 = ((j + (ring ? .5 : 0)) / nr) * Math.PI * 2 + (rand(k * 3) - .5) * .12;
          const R = ring ? [.40, .39] : [.27, .29], spd = .07;
          t.style.left = "50%"; t.style.top = "50%";
          const born = .35 + k * .07;
          addAnim(sc, t, born, sc.dur, (t, p, lt) => {
            const a = a0 + (lt + born) * spd, depth = (Math.sin(a) + 1) / 2;   // 0 远 1 近
            const x = Math.cos(a) * R[0] * W * (LAND ? 1 : .9), y = Math.sin(a) * R[1] * H * (LAND ? 1.02 : .7);
            const pop = E.back(clamp(lt / .55)), s = lerp(.72, 1.08, depth) * pop;
            t.style.opacity = clamp(lt * 3) * lerp(.62, 1, depth); t.style.zIndex = Math.round(depth * 10);
            t.style.filter = `blur(${(1 - depth) * 1.1}px)`;
            t.style.transform = `translate(-50%,-50%) translate(${x}px, ${y}px) scale(${s})`;
          });
        }
      });
      camInit(sc, { s: 1.15, r: -3 }); camMove(sc, 0, 1.4, { s: 1, r: 0 }, E.soft); camMove(sc, 1.4, sc.dur - 1.4, { s: 1.05, r: 1.5 }, E.lin);
    },
    gallery(sc, d, el) { // 多张截图墙，倾斜着从镜头前飞过
      const tb = textBlock(sc, d, "copy center mid over"); el.appendChild(tb);
      const wall = h("div", "wall"); el.insertBefore(wall, tb);
      const cols = LAND ? 4 : 3;
      for (let c = 0; c < cols; c++) {
        const col = h("div", "wcol"); wall.appendChild(col);
        for (let r = 0; r < 4; r++) { const im = h("div", "wimg"); im.style.backgroundImage = `url("${d.images[(c * 4 + r) % d.images.length]}")`; col.appendChild(im); }
        addAnim(sc, col, 0, sc.dur, (col, p, lt) => { col.style.opacity = 1; col.style.transform = `translateY(${(c % 2 ? -1 : 1) * (lt * 55) - (c % 2 ? 0 : 400) + (1 - E.out5(clamp(lt / 1.2))) * (c % 2 ? 600 : -600)}px)`; });
      }
      addAnim(sc, wall, 0, .8, (w, p) => w.style.opacity = E.out3(p), { keep: true });
      animCopy(sc, tb, .6);
      camInit(sc, { s: 1.35, r: 4 }); camMove(sc, 0, 1.6, { s: 1.02, r: 0 }, E.soft); drift(sc, 1.6, .8);
    },
    end(sc, d, el) {
      ghost(sc, el, P.brand.name, -1);
      const lg = logoEl("logo small"); el.appendChild(lg);
      const tb = textBlock(sc, { title: d.title || P.brand.slogan, sub: d.sub }, "copy center"); el.appendChild(tb);
      rings(sc, el, .3, 3, { size: LAND ? 3 : 2.4, alpha: .4 });
      if (d.cta) {
        const b = h("div", "cta", rich(d.cta)); el.appendChild(b); IMAGE.popBounce(sc, b, 1.2);
        addAnim(sc, b, 2.2, sc.dur, (el, p, lt) => { el.style.scale = 1 + Math.max(0, Math.sin(lt * 4)) * .035; }, { keep: true });
      }
      (S.logoIn || IMAGE.popBounce)(sc, lg, .1);
      sheen(sc, lg, .9);
      animCopy(sc, tb, .45);
      camInit(sc, { s: 1.3 }); camMove(sc, 0, 1.6, { s: 1 }, E.soft); drift(sc, 1.6, .6);
    },
  };

  // ---------- 时间轴：场景时长由旁白长度决定 ----------
  const TD = S.transitionDur ?? .6;
  const MIN = { logo: 3.2, slogan: 3.0, feature: 4.5, cards: 4.5, stats: 4.0, tags: 4.2, gallery: 4.0, end: 4.0 };
  {
    let t = 0;
    P.scenes.forEach((d, i) => {
      const lead = i ? TD + .1 : .5, vd = d.voice?.dur || 0;
      d.dur = Math.max((d.min || MIN[d.type] || 3.5) * (S.pace || 1), vd ? lead + vd + .35 + (i < P.scenes.length - 1 ? TD : .8) : 0);
      d.start = t;
      if (d.voice) { d.voice.start = t + lead; (d.voice.cues || []).forEach(c => { c.start += d.voice.start; c.end += d.voice.start; }); }
      t += d.dur - TD;
    });
    const last = P.scenes[P.scenes.length - 1];
    P.duration = +(last.start + last.dur).toFixed(3);
    window.PV_TIMELINE = { duration: P.duration, fps: P.fps, scenes: P.scenes.map(d => ({ type: d.type, start: d.start, dur: d.dur, voice: d.voice ? { file: d.voice.file, start: d.voice.start, dur: d.voice.dur } : null })) };
  }

  // ---------- 搭场景 ----------
  const TLIST = S.transitions || [S.transition || "fade"];
  const scenes = P.scenes.map((d, idx) => {
    const wrap = h("section", "scene-wrap"); wrap.style.opacity = 0;
    const el = h("div", `scene t-${d.type}` + (d.theme ? " theme-" + d.theme : "")); wrap.appendChild(el);
    stage.appendChild(wrap);
    const sc = { idx, el, wrap, start: d.start, dur: d.dur, d };
    (LAYOUT[d.type] || LAYOUT.slogan)(sc, d, el, idx);
    if (S.sceneHook) S.sceneHook(sc, d, wrap, { h, addAnim, TEXT, IMAGE });
    sc.trans = d.transition || TLIST[(idx + TLIST.length - 1) % TLIST.length];
    return sc;
  });
  window.DURATION = P.duration;

  // 背景 / 装饰层（风格自带）。背景跟着镜头做视差，移动幅度只有前景的三分之一
  const bg = document.getElementById("bg");
  const bgUpdate = S.bg ? S.bg(bg, { h, P, rand }) : null;

  // 字幕
  const cap = document.getElementById("cap");
  const cues = [];
  if (P.captions) P.scenes.forEach(d => (d.voice?.cues || []).forEach(c => cues.push(c)));

  // 每帧先把所有动画元素放回初始态，再按时间推进（保证可任意 seek）
  function reset(el) { el.style.opacity = 0; el.style.transform = ""; el.style.filter = ""; el.style.clipPath = ""; }

  function seek(t) {
    fx.style.display = "none"; fx.style.opacity = ""; fx.style.transform = "";
    let camMain = null;
    for (const sc of scenes) {
      const vis = t >= sc.start - .0001 && t < sc.start + sc.dur;
      sc.wrap.style.display = vis ? "" : "none";
      sc.wrap.style.opacity = vis ? 1 : 0; sc.wrap.style.transform = ""; sc.wrap.style.filter = ""; sc.wrap.style.clipPath = "";
      if (!vis) continue;
      // 镜头 + 运动模糊（镜头动得快时糊一点，像真的摄影机）
      const lt = t - sc.start, c = camAt(sc, lt), c0 = camAt(sc, lt - 1 / 30);
      const v = Math.hypot(c.x - c0.x, c.y - c0.y) + Math.abs(c.s - c0.s) * W * .5 + Math.abs(c.r - c0.r) * 20;
      const s = Math.max(c.s, 1 + 2 * Math.max(Math.abs(c.x) / W, Math.abs(c.y) / H));
      sc.el.style.transform = `translate(${c.x}px, ${c.y}px) rotate(${c.r}deg) scale(${s})`;
      sc.el.style.filter = v > 22 ? `blur(${Math.min((v - 22) * .08, 5).toFixed(2)}px)` : "";
      if (!camMain || lt < sc.dur - TD) camMain = c;
    }
    for (const a of anims) {
      const sc = scenes[a.scene.idx];
      if (sc.wrap.style.display === "none") continue;
      const lt = t - sc.start - a.at;
      if (lt < 0) { if (a.extra.keep) { a.el.style.scale = ""; a.fn(a.el, 0, 0, a.extra); } else reset(a.el); continue; }
      if (!a.extra.keep) a.el.style.opacity = 1;
      a.fn(a.el, clamp(lt / a.dur), lt, a.extra);
    }
    // 转场：第 i 场最后 TD 秒和第 i+1 场开头重叠
    for (let i = 0; i < scenes.length - 1; i++) {
      const a = scenes[i], b = scenes[i + 1], s = b.start, e = a.start + a.dur;
      if (t >= s && t < e) (TRANS[b.trans] || TRANS.fade)(a.wrap, b.wrap, clamp((t - s) / (e - s)));
    }
    // 最后一场收尾淡出
    const last = scenes[scenes.length - 1];
    if (t > P.duration - .5) last.wrap.style.opacity = clamp((P.duration - t) / .5);
    if (camMain) bg.style.transform = `translate(${camMain.x * .3}px, ${camMain.y * .3}px) scale(${1 + (camMain.s - 1) * .35}) rotate(${camMain.r * .3}deg)`;
    if (bgUpdate) bgUpdate(t);
    if (cap) {
      const c = cues.find(c => t >= c.start && t < c.end);
      cap.innerHTML = c ? `<span>${esc(c.text)}</span>` : ""; cap.style.opacity = c ? 1 : 0;
    }
  }
  window.seek = seek;
  // 浏览器里直接打开时：自动播放预览
  const q = new URLSearchParams(location.search);
  if (!window.__PV_RENDER__) {
    if (q.has("t")) seek(parseFloat(q.get("t")));
    else {
      const t0 = performance.now();
      const audio = document.getElementById("vo"); if (audio) audio.play().catch(() => {});
      const loop = () => { const t = ((performance.now() - t0) / 1000) % P.duration; seek(t); requestAnimationFrame(loop); };
      loop();
    }
  }
})();
