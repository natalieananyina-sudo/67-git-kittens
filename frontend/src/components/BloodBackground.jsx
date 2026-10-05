// Живой фон: сеть кровеносных сосудов «прорастает» на экране (искусственный ангиогенез),
// затем по ней текут клетки крови: эритроциты, немного тромбоцитов и редкие лейкоциты.
//
// Почему canvas, а не SVG/CSS: сотня движущихся клеток и рост сосудов дешевле рисовать одним холстом.
// Готовая сеть сосудов кэшируется в отдельный (невидимый) холст, поэтому каждый кадр рисуются только клетки.
//
// mode="login"     — анимация ярче и быстрее (экран входа);
// mode="workspace" — бледнее, медленнее и меньше клеток (рабочая область, ничто не отвлекает от данных).
// При смене режима параметры меняются плавно, а сама сеть не перерисовывается заново.
import { useEffect, useRef } from "react";

const PROFILES = {
  login: { speed: 1, cells: 1, vessels: 1 },
  workspace: { speed: 0.35, cells: 0.45, vessels: 0.7 },
};
const MAX_CELLS = 110;
const GROW_SPEED = 240; // скорость роста сосудов, пикселей в секунду

// Детерминированный генератор случайных чисел: сеть сосудов одинаковая при каждом открытии
function mulberry32(seed) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Точки кубической кривой Безье с накопленной длиной (для движения клеток вдоль сосуда)
function sampleBezier(p0, p1, p2, p3) {
  const approx = Math.hypot(p3[0] - p0[0], p3[1] - p0[1]) * 1.15;
  const n = Math.max(8, Math.ceil(approx / 5));
  const pts = new Float32Array((n + 1) * 2);
  const cum = new Float32Array(n + 1);
  let prevX = p0[0];
  let prevY = p0[1];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const u = 1 - t;
    const x = u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0];
    const y = u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1];
    pts[i * 2] = x;
    pts[i * 2 + 1] = y;
    cum[i] = i === 0 ? 0 : cum[i - 1] + Math.hypot(x - prevX, y - prevY);
    prevX = x;
    prevY = y;
  }
  return { pts, cum, len: cum[n] };
}

// Строит дерево сосудов: несколько стволов входят с краёв экрана и ветвятся
function buildVessels(width, height) {
  const rand = mulberry32(20261005);
  const scale = Math.min(width, height) / 900 + 0.25;
  const segments = [];
  const margin = 120;
  const outside = (x, y) => x < -margin || y < -margin || x > width + margin || y > height + margin;

  function grow(start, angle, w, generation, step, startTime, parent) {
    if (segments.length > 70 || w < 2.2 || generation > 2 || step > 12) return;
    const len = (110 + rand() * 120) * scale * (generation === 0 ? 1.25 : 0.9);
    const bend = (rand() - 0.5) * 0.9;
    const a1 = angle + bend * 0.5;
    const a2 = angle + bend;
    const end = [start[0] + Math.cos(a2) * len, start[1] + Math.sin(a2) * len];
    const c1 = [start[0] + Math.cos(angle) * len * 0.35, start[1] + Math.sin(angle) * len * 0.35];
    const c2 = [end[0] - Math.cos(a1) * len * 0.35, end[1] - Math.sin(a1) * len * 0.35];
    const seg = { ...sampleBezier(start, c1, c2, end), width: w, children: [], start: startTime, root: !parent };
    seg.dur = seg.len / GROW_SPEED;
    segments.push(seg);
    if (parent) parent.children.push(seg);
    if (outside(end[0], end[1])) return;

    const next = startTime + seg.dur;
    // продолжение сосуда
    grow(end, a2 + (rand() - 0.5) * 0.5, w * (generation === 0 ? 0.94 : 0.86), generation, step + 1, next, seg);
    // боковая ветвь (чем тоньше сосуд, тем реже ветвится)
    if (rand() < (generation === 0 ? 0.5 : 0.28)) {
      const side = rand() < 0.5 ? -1 : 1;
      grow(end, a2 + side * (0.55 + rand() * 0.6), w * 0.62, generation + 1, step + 1, next + 0.15, seg);
    }
  }

  const base = 15 * scale;
  // стволы: слева, сверху справа, снизу, справа
  grow([-40, height * 0.28], 0.25, base, 0, 0, 0.2, null);
  grow([width * 0.78, -40], 1.95, base * 0.9, 0, 0, 0.6, null);
  grow([width * 0.3, height + 40], -1.35, base * 0.85, 0, 0, 1.0, null);
  grow([width + 40, height * 0.68], 3.3, base * 0.95, 0, 0, 1.4, null);
  const growEnd = Math.max(...segments.map((s) => s.start + s.dur));
  return { segments, roots: segments.filter((s) => s.root), maxWidth: base, growEnd };
}

// Точка и направление на расстоянии d вдоль сегмента
function pointAt(seg, d) {
  const { cum, pts } = seg;
  let lo = 0;
  let hi = cum.length - 1;
  while (lo < hi - 1) {
    const mid = (lo + hi) >> 1;
    if (cum[mid] < d) lo = mid;
    else hi = mid;
  }
  const span = cum[hi] - cum[lo] || 1;
  const t = Math.min(1, Math.max(0, (d - cum[lo]) / span));
  const x0 = pts[lo * 2];
  const y0 = pts[lo * 2 + 1];
  const x1 = pts[hi * 2];
  const y1 = pts[hi * 2 + 1];
  return { x: x0 + (x1 - x0) * t, y: y0 + (y1 - y0) * t, angle: Math.atan2(y1 - y0, x1 - x0) };
}

// Отрисовка сосудов в три прохода: свечение, стенка, просвет (так развилки получаются бесшовными)
function drawVessels(ctx, segments, time) {
  const passes = [
    { extra: 9, color: "rgba(80, 180, 235, 0.05)", k: 1 },
    { extra: 0, color: "rgba(130, 210, 245, 0.17)", k: 1 },
    { extra: 0, color: "rgba(3, 28, 48, 0.55)", k: 0.6 },
  ];
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const pass of passes) {
    ctx.strokeStyle = pass.color;
    for (const seg of segments) {
      const grown = time === Infinity ? seg.len : Math.min(seg.len, (time - seg.start) * GROW_SPEED);
      if (grown <= 0) continue;
      ctx.lineWidth = seg.width * pass.k + pass.extra;
      ctx.beginPath();
      ctx.moveTo(seg.pts[0], seg.pts[1]);
      for (let i = 1; i < seg.cum.length && seg.cum[i] <= grown; i++) ctx.lineTo(seg.pts[i * 2], seg.pts[i * 2 + 1]);
      if (grown < seg.len) {
        const tip = pointAt(seg, grown);
        ctx.lineTo(tip.x, tip.y);
      }
      ctx.stroke();
    }
  }
  // светящиеся «верхушки» растущих сосудов (как эндотелиальные клетки-лидеры при ангиогенезе)
  if (time !== Infinity) {
    for (const seg of segments) {
      const grown = (time - seg.start) * GROW_SPEED;
      if (grown <= 0 || grown >= seg.len) continue;
      const tip = pointAt(seg, grown);
      const glow = ctx.createRadialGradient(tip.x, tip.y, 0, tip.x, tip.y, seg.width + 10);
      glow.addColorStop(0, "rgba(190, 240, 255, 0.55)");
      glow.addColorStop(1, "rgba(190, 240, 255, 0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(tip.x, tip.y, seg.width + 10, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

// Насколько ярко рисовать клетку в точке (x, y): в центре экрана, где текст и формы, — бледнее
function centerMask(x, y, width, height) {
  const nx = (x - width / 2) / (width * 0.34);
  const ny = (y - height * 0.45) / (height * 0.44);
  const r2 = nx * nx + ny * ny;
  return r2 >= 1 ? 1 : 0.3 + 0.7 * r2;
}

// Стирает часть сосудов под центральной областью (под текстом), сохраняя их по краям
function fadeCenter(ctx, width, height) {
  const r = Math.max(width, height) * 0.42;
  const g = ctx.createRadialGradient(width / 2, height * 0.45, 0, width / 2, height * 0.45, r);
  g.addColorStop(0, "rgba(0, 0, 0, 0.6)");
  g.addColorStop(0.55, "rgba(0, 0, 0, 0.35)");
  g.addColorStop(1, "rgba(0, 0, 0, 0)");
  ctx.save();
  ctx.globalCompositeOperation = "destination-out";
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, width, height);
  ctx.restore();
}

// Спрайты клеток рисуются один раз и затем только копируются (быстрее, чем градиенты в каждом кадре)
function makeSprites() {
  const make = (size, draw) => {
    const c = document.createElement("canvas");
    c.width = c.height = size;
    draw(c.getContext("2d"), size / 2);
    return c;
  };
  // Эритроцит: двояковогнутый диск — плотный ободок и светлый «провал» в центре
  const rbc = make(48, (g, r) => {
    const grad = g.createRadialGradient(r, r, 0, r, r, r);
    grad.addColorStop(0, "rgba(143, 216, 250, 0.16)");
    grad.addColorStop(0.45, "rgba(143, 216, 250, 0.22)");
    grad.addColorStop(0.78, "rgba(185, 236, 255, 0.75)");
    grad.addColorStop(0.95, "rgba(185, 236, 255, 0.25)");
    grad.addColorStop(1, "rgba(185, 236, 255, 0)");
    g.fillStyle = grad;
    g.beginPath();
    g.arc(r, r, r, 0, Math.PI * 2);
    g.fill();
  });
  // Тромбоцит: маленький неровный фрагмент
  const platelet = make(24, (g, r) => {
    g.fillStyle = "rgba(205, 242, 255, 0.55)";
    for (const [dx, dy, rr] of [[0, 0, 0.42], [0.28, -0.15, 0.3], [-0.22, 0.2, 0.28]]) {
      g.beginPath();
      g.arc(r + dx * r, r + dy * r, rr * r, 0, Math.PI * 2);
      g.fill();
    }
  });
  // Лейкоцит: крупная бледная клетка с сегментированным ядром
  const wbc = make(64, (g, r) => {
    const grad = g.createRadialGradient(r, r, r * 0.2, r, r, r);
    grad.addColorStop(0, "rgba(220, 245, 255, 0.22)");
    grad.addColorStop(0.85, "rgba(220, 245, 255, 0.3)");
    grad.addColorStop(1, "rgba(220, 245, 255, 0)");
    g.fillStyle = grad;
    g.beginPath();
    g.arc(r, r, r, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = "rgba(150, 215, 248, 0.5)";
    for (const [dx, dy] of [[-0.28, -0.1], [0.05, -0.28], [0.3, 0.05], [0.0, 0.25]]) {
      g.beginPath();
      g.arc(r + dx * r, r + dy * r, r * 0.2, 0, Math.PI * 2);
      g.fill();
    }
  });
  return { rbc, platelet, wbc };
}

export default function BloodBackground({ mode = "login" }) {
  const canvasRef = useRef(null);
  const targetRef = useRef(PROFILES[mode] ?? PROFILES.login);

  // Новый режим: меняем только «цель», текущие параметры плавно к ней подтягиваются в цикле анимации
  useEffect(() => {
    targetRef.current = PROFILES[mode] ?? PROFILES.login;
  }, [mode]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const sprites = makeSprites();
    const rand = Math.random;
    const current = { ...targetRef.current };
    let net = null;
    let vesselCache = null;
    let cells = [];
    let width = 0;
    let height = 0;
    let dpr = 1;
    let clock = 0;
    let frame = 0;
    let lastTime = 0;
    let rafId = 0;
    let resizeTimer = 0;

    function setup(regrow) {
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      net = buildVessels(width, height);
      vesselCache = null;
      if (!regrow) clock = net.growEnd + 1; // при изменении размера окна сеть сразу готова
      cells = Array.from({ length: MAX_CELLS }, (_, i) => newCell(i, true));
    }

    function pickRoot() {
      const total = net.roots.reduce((sum, r) => sum + r.width, 0);
      let pick = rand() * total;
      for (const r of net.roots) {
        pick -= r.width;
        if (pick <= 0) return r;
      }
      return net.roots[0];
    }

    function newCell(i, scatter) {
      const r = rand();
      const type = r < 0.03 ? "wbc" : r < 0.12 ? "platelet" : "rbc";
      const seg = pickRoot();
      return {
        i,
        type,
        seg,
        d: scatter ? rand() * seg.len : -rand() * 900, // отрицательное расстояние = клетка ещё «за экраном»
        offset: (rand() - 0.5) * 0.55, // смещение поперёк просвета сосуда
        wobble: rand() * Math.PI * 2,
        tumble: rand() * Math.PI * 2, // эритроциты кувыркаются в потоке
        jitter: 0.75 + rand() * 0.5,
        alpha: scatter ? 1 : 0,
      };
    }

    // Клетка дошла до конца сегмента: выбираем дочерний сосуд (широкие — чаще), иначе начинаем заново
    function advance(cell) {
      const ready = cell.seg.children.filter((c) => clock >= c.start + c.dur);
      if (!ready.length) return Object.assign(cell, newCell(cell.i, false));
      const total = ready.reduce((s, c) => s + c.width, 0);
      let pick = rand() * total;
      for (const c of ready) {
        pick -= c.width;
        if (pick <= 0) {
          cell.seg = c;
          break;
        }
      }
      cell.d = 0;
      return cell;
    }

    function drawCell(cell, sizeBase) {
      const seg = cell.seg;
      const p = pointAt(seg, cell.d);
      const lateral = cell.offset * seg.width * 0.7 + Math.sin(cell.wobble) * seg.width * 0.08;
      const x = p.x - Math.sin(p.angle) * lateral;
      const y = p.y + Math.cos(p.angle) * lateral;
      const isLeaf = seg.children.length === 0;
      const fadeEnd = isLeaf ? Math.min(1, (seg.len - cell.d) / 40) : 1;
      const visible = cell.i < MAX_CELLS * current.cells ? 1 : 0;
      const alpha = Math.max(0, Math.min(1, cell.alpha)) * fadeEnd * visible * centerMask(x, y, width, height);
      if (alpha <= 0.01) return;

      let sprite = sprites.rbc;
      let size = Math.min(11, Math.max(4.5, seg.width * 0.62)) * sizeBase;
      let squash = 0.35 + 0.65 * Math.abs(Math.cos(cell.tumble)); // диск, видимый под разными углами
      if (cell.type === "platelet") {
        sprite = sprites.platelet;
        size *= 0.45;
        squash = 1;
      } else if (cell.type === "wbc") {
        sprite = sprites.wbc;
        size *= 1.5;
        squash = 1;
      }
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.translate(x, y);
      ctx.rotate(p.angle + (cell.type === "rbc" ? 0 : cell.tumble));
      ctx.scale(1, squash);
      ctx.drawImage(sprite, -size / 2, -size / 2, size, size);
      ctx.restore();
    }

    function render(dt) {
      // плавный переход параметров к режиму страницы
      const k = 1 - Math.exp(-dt / 1.2);
      for (const key of Object.keys(current)) current[key] += (targetRef.current[key] - current[key]) * k;

      ctx.clearRect(0, 0, width, height);
      const growing = clock < net.growEnd;
      ctx.globalAlpha = current.vessels;
      if (growing) {
        drawVessels(ctx, net.segments, clock);
        fadeCenter(ctx, width, height);
      } else {
        if (!vesselCache) {
          vesselCache = document.createElement("canvas");
          vesselCache.width = canvas.width;
          vesselCache.height = canvas.height;
          const g = vesselCache.getContext("2d");
          g.setTransform(dpr, 0, 0, dpr, 0, 0);
          drawVessels(g, net.segments, Infinity);
          fadeCenter(g, width, height);
        }
        ctx.drawImage(vesselCache, 0, 0, width, height);
      }
      ctx.globalAlpha = 1;

      const sizeBase = Math.min(width, height) / 900 + 0.35;
      for (const cell of cells) {
        const seg = cell.seg;
        if (clock < seg.start + seg.dur) continue; // сосуд ещё растёт: клетки пойдут, когда он сформируется
        // в широких сосудах кровь течёт быстрее, чем в тонких
        const v = (26 + 70 * (seg.width / net.maxWidth)) * cell.jitter * current.speed;
        cell.d += v * dt;
        cell.wobble += dt * 1.3;
        cell.tumble += dt * (cell.type === "rbc" ? 1.6 : 0.6) * current.speed;
        if (cell.d >= 0) cell.alpha = Math.min(1, cell.alpha + dt * 1.5);
        if (cell.d >= seg.len) advance(cell);
        if (cell.d >= 0) drawCell(cell, sizeBase);
      }
    }

    function loop(now) {
      rafId = requestAnimationFrame(loop);
      const dt = Math.min(0.05, (now - (lastTime || now)) / 1000);
      lastTime = now;
      frame += 1;
      // в рабочей области достаточно 30 кадров в секунду — экономим ресурсы ноутбука
      if (targetRef.current === PROFILES.workspace && clock > net.growEnd && frame % 2) return;
      clock += targetRef.current === PROFILES.workspace && clock > net.growEnd ? dt * 2 : dt;
      render(targetRef.current === PROFILES.workspace && clock > net.growEnd ? dt * 2 : dt);
    }

    function onResize() {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        setup(false);
        if (reduceMotion) render(0);
      }, 200);
    }

    setup(!reduceMotion);
    if (reduceMotion) {
      // без анимации: готовая сеть и неподвижные клетки
      clock = net.growEnd + 1;
      render(0);
    } else {
      cells.forEach((c) => (c.alpha = 0));
      rafId = requestAnimationFrame(loop);
    }
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(rafId);
      clearTimeout(resizeTimer);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <div className={`bg ${mode === "login" ? "" : "bg-calm"}`} aria-hidden="true">
      <canvas ref={canvasRef} className="blood-canvas" />
    </div>
  );
}
