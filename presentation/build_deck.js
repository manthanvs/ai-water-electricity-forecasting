// Render presentation/deck.json (written by make_deck_json.py) into the final .pptx with pptxgenjs.
// This file holds layout only: every word and number comes from deck.json.
//   node presentation/build_deck.js
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const HERE = __dirname;
const ROOT = path.resolve(HERE, "..");
const OUT = path.join(HERE, "out", "Final_Presentation_Manthan_Sankpal.pptx");
const deck = JSON.parse(fs.readFileSync(path.join(HERE, "deck.json"), "utf8"));

// Design system (03_FINAL_PRESENTATION.md, section D)
const C = { navy: "0B2545", cyan: "1AA7D6", deep: "13315C", panel: "F2F6FA", yellow: "F2C94C", grey: "5A6472", white: "FFFFFF", rule: "C9D3DE" };
const FONT = "Calibri";
const W = 13.333, H = 7.5, MX = 0.5;
const CONTENT_W = W - 2 * MX;
const SIDE_W = 3.6, GAP = 0.3;

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Manthan Sankpal";
pptx.title = deck.slides[0].title;
pptx.theme = { headFontFace: FONT, bodyFontFace: FONT };

const asset = (p) => path.join(ROOT, p);
const txt = (o) => ({ fontFace: FONT, color: C.navy, margin: 0, ...o });

function chrome(s, slide, withTitle = true) {
  s.background = { color: C.white };
  s.addImage({ path: asset(deck.logo_small), x: W - MX - 0.72, y: 0.28, w: 0.72, h: 0.72 });
  s.addText(deck.footer, txt({ x: MX, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: C.grey, valign: "middle" }));
  s.addText(slide.number, txt({ x: W - MX - 1, y: 7.0, w: 1, h: 0.3, fontSize: 10, color: C.grey, align: "right", valign: "middle" }));
  if (withTitle) {
    s.addText(slide.title, txt({ x: MX, y: 0.32, w: W - 2 * MX - 1.0, h: 0.72, fontSize: 30, bold: true, valign: "middle" }));
    s.addShape(pptx.ShapeType.rect, { x: MX, y: 1.1, w: 1.3, h: 0.06, fill: { color: C.cyan }, line: { color: C.cyan, width: 0 } });
  }
}

function box(s, x, y, w, h, fill, accent) {
  s.addShape(pptx.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill, width: 0 } });
  if (accent) s.addShape(pptx.ShapeType.rect, { x, y: y + 0.12, w: 0.08, h: h - 0.24, fill: { color: accent }, line: { color: accent, width: 0 } });
}

function contain(px, x, y, w, h) {
  const k = Math.min(w / px[0], h / px[1]);
  const iw = px[0] * k, ih = px[1] * k;
  return { x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih };
}

function lineRuns(lines, size, bullets) {
  return lines.map((l, i) => {
    const plain = /^[+–-] /.test(l) || !bullets;
    return { text: l, options: { fontSize: size, breakLine: i < lines.length - 1, bullet: plain ? false : { indent: 16 }, paraSpaceAfter: 6 } };
  });
}

// ------------------------------------------------------------------ blocks
function figure(s, b, x, y, w, h) {
  s.addImage({ path: asset(b.path), ...contain(b.px, x, y, w, h) });
}

function bullets(s, b, x, y, w, h) {
  // numbers are written out: LibreOffice restarts auto-numbering on every paragraph
  const runs = b.items.map((it, i) => ({
    text: b.numbered ? `${i + 1}.  ${it}` : it,
    options: { breakLine: i < b.items.length - 1, bullet: b.numbered ? false : { indent: 24 }, paraSpaceAfter: 14 },
  }));
  s.addText(runs, txt({ x, y, w, h, fontSize: 22, valign: "top" }));
}

function panels(s, b, x, y, w, h) {
  const cols = b.cols, rows = Math.ceil(b.items.length / cols), g = 0.25;
  const pw = (w - g * (cols - 1)) / cols, ph = (h - g * (rows - 1)) / rows;
  b.items.forEach((p, i) => {
    const px = x + (i % cols) * (pw + g), py = y + Math.floor(i / cols) * (ph + g);
    box(s, px, py, pw, ph, C.panel, p.highlight ? C.yellow : C.cyan);
    const runs = [{ text: p.head, options: { fontSize: 22, bold: true, breakLine: true, paraSpaceAfter: 8 } }, ...lineRuns(p.lines, cols >= 3 ? 18 : 20, true)];
    s.addText(runs, txt({ x: px + 0.3, y: py + 0.15, w: pw - 0.5, h: ph - 0.3, valign: "top" }));
  });
}

function table(s, b, x, y, w, h) {
  const total = b.widths.reduce((a, v) => a + v, 0);
  const colW = b.widths.map((v) => (v / total) * w);
  const fs = b.font || 14;
  const head = b.header.map((t) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.deep }, align: "center", valign: "middle" } }));
  const rows = b.rows.map((r, i) => r.map((t, j) => ({
    text: t, options: { fill: { color: i % 2 ? C.white : C.panel }, align: j === 0 ? "left" : "center", valign: "middle", bold: /\*$/.test(t) },
  })));
  s.addTable([head, ...rows], { x, y, w, colW, fontFace: FONT, fontSize: fs, color: C.navy, margin: [3, 5, 3, 5],
    border: { type: "solid", pt: 0.75, color: C.rule }, autoPage: false });
}

function text(s, b, x, y, w, h) {
  s.addText(lineRuns(b.lines, b.size || 20, false), txt({ x, y, w, h, valign: "top", paraSpaceAfter: 14 }));
}

function references(s, b, x, y, w, h) {
  const runs = [];
  b.refs.forEach((r, i) => {
    runs.push({ text: `[${r.n}]  `, options: { fontSize: 12 } });
    r.runs.forEach((t, j) => runs.push({ text: t.text, options: { fontSize: 12, italic: t.italic,
      breakLine: j === r.runs.length - 1 && i < b.refs.length - 1, paraSpaceAfter: 6 } }));
  });
  s.addText(runs, txt({ x, y, w, h, valign: "top" }));
}

const BLOCKS = { figure, bullets, panels, table, text, references };

// ------------------------------------------------------------------ tiles
function tiles(s, list, x, y, w, h) {
  const g = 0.2, n = list.length;
  const th = Math.min(1.75, (h - g * (n - 1)) / n);
  list.forEach((t, i) => {
    const ty = y + i * (th + g);
    const hi = !!t.highlight;
    const tileH = t.kind === "info" ? Math.max(th, 1.5) : th;
    box(s, x, ty, w, tileH, hi ? C.yellow : C.panel, hi ? C.navy : C.cyan);
    const runs = t.kind === "kpi"
      ? [{ text: t.value, options: { fontSize: 32, bold: true, breakLine: true } },
         { text: t.label, options: { fontSize: 14, color: hi ? C.navy : C.grey } }]
      : [{ text: t.head, options: { fontSize: 18, bold: true, breakLine: true, paraSpaceAfter: 4 } }, ...lineRuns(t.lines, 16, false)];
    s.addText(runs, txt({ x: x + 0.28, y: ty + 0.1, w: w - 0.42, h: tileH - 0.2, valign: "middle" }));
  });
}

// ------------------------------------------------------------------ layouts
function titleSlide(sl) {
  const s = pptx.addSlide();
  s.background = { color: C.white };
  s.addImage({ path: asset(deck.logo_large), x: (W - 2.4) / 2, y: 0.35, w: 2.4, h: 1.8 });
  s.addText(sl.title, txt({ x: 1.2, y: 2.3, w: W - 2.4, h: 1.25, fontSize: 36, bold: true, align: "center", valign: "middle" }));
  s.addShape(pptx.ShapeType.rect, { x: (W - 2.2) / 2, y: 3.68, w: 2.2, h: 0.07, fill: { color: C.cyan }, line: { color: C.cyan, width: 0 } });
  s.addText(sl.subtitle, txt({ x: 1.2, y: 3.9, w: W - 2.4, h: 0.5, fontSize: 22, color: C.deep, align: "center", valign: "middle" }));
  s.addText(sl.lines.map((l, i) => ({ text: l, options: { breakLine: i < sl.lines.length - 1, paraSpaceAfter: 8 } })),
    txt({ x: 1.2, y: 4.6, w: W - 2.4, h: 2.3, fontSize: 18, align: "center", valign: "top" }));
  s.addNotes(sl.notes);
}

function thanksSlide(sl) {
  const s = pptx.addSlide();
  chrome(s, sl, false);
  s.addText(sl.title, txt({ x: MX, y: 2.0, w: CONTENT_W, h: 1.1, fontSize: 48, bold: true, align: "center", valign: "middle" }));
  s.addShape(pptx.ShapeType.rect, { x: (W - 2.2) / 2, y: 3.2, w: 2.2, h: 0.07, fill: { color: C.cyan }, line: { color: C.cyan, width: 0 } });
  s.addText(sl.subtitle, txt({ x: MX, y: 3.45, w: CONTENT_W, h: 0.6, fontSize: 26, color: C.deep, align: "center", valign: "middle" }));
  s.addText(sl.lines.map((l, i) => ({ text: l, options: { breakLine: i < sl.lines.length - 1, paraSpaceAfter: 6 } })),
    txt({ x: MX, y: 4.5, w: CONTENT_W, h: 1.0, fontSize: 18, align: "center", valign: "top" }));
  s.addNotes(sl.notes);
}

function contentSlide(sl) {
  const s = pptx.addSlide();
  chrome(s, sl);
  let top = 1.4;
  if (sl.takeaway) {
    s.addText(sl.takeaway, txt({ x: MX, y: 1.3, w: CONTENT_W, h: 0.55, fontSize: 20, italic: true, color: C.deep, valign: "middle" }));
    top = 2.0;
  }
  const bottom = sl.footnote ? 6.4 : 6.85;
  if (sl.footnote) {
    s.addText(sl.footnote, txt({ x: MX, y: 6.45, w: CONTENT_W, h: 0.42, fontSize: 14, italic: true, color: C.grey, valign: "middle" }));
  }
  let mx = MX, mw = CONTENT_W;
  if (sl.tiles) {
    const tx = sl.side === "left" ? MX : W - MX - SIDE_W;
    tiles(s, sl.tiles, tx, top, SIDE_W, bottom - top);
    mw = CONTENT_W - SIDE_W - GAP;
    mx = sl.side === "left" ? MX + SIDE_W + GAP : MX;
  }
  const blocks = sl.blocks || [];
  const fixed = blocks.reduce((a, b) => a + (b.h || 0), 0);
  const flex = blocks.filter((b) => !b.h).length;
  let y = top;
  blocks.forEach((b) => {
    const h = b.h || (bottom - top - fixed - 0.2 * (blocks.length - 1)) / flex;
    BLOCKS[b.type](s, b, mx, y, mw, h);
    y += h + 0.2;
  });
  s.addNotes(sl.notes);
}

for (const sl of deck.slides) {
  ({ title: titleSlide, thanks: thanksSlide, content: contentSlide })[sl.layout](sl);
}
fs.mkdirSync(path.dirname(OUT), { recursive: true });
pptx.writeFile({ fileName: OUT }).then((f) => console.log(`wrote ${f}`));
