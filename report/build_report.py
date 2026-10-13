"""Build the seminar report from report/content/*.md with the official format (report/docx_format.py).

    python report/build_report.py            draft build (CONFIRM markers and unresolved tokens are highlighted)
    python report/build_report.py --final    final build (any CONFIRM marker or unresolved token is an error)

Markup (see docs/instructions/02_SEMINAR_REPORT.md, section D):
    # Title / ## Section / ### Sub-heading; blank-line paragraphs; "- item" bullets; "1. item" numbered lists;
    **bold**, *italic*, _{subscript}, ^{superscript}; <!-- comments --> are dropped.
    [[FIG:id]] [[TAB:id]] [[EQ:id]] place a figure / table / equation (registries: figures.yaml, equations.yaml).
    {{fig:id}} {{tab:id}} {{eq:id}} in-text references; [@key] or [@k1; @k2] citations (IEEE, order of first use).
    {{m:path|fmt}} metrics.json, {{a:...}} anomaly.json, {{o:...}} optimisation.json, {{e:...}} eda_summary.json,
    {{c:...}} config/config.yaml, {{f:key}} report/facts.yaml (cited statistics). In m: paths "SEL" stands for the
    selected model of that resource and horizon. fmt is a Python format spec or one of: name, date, len, p, int.
    [[CONFIRM: ...]] is highlighted and listed.
Page numbers in the contents and lists use two passes through LibreOffice (docx_format.page_map).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import docx_format as F  # noqa: E402

CONTENT, OUT = HERE / "content", HERE / "out"
TEMPLATE = ROOT / "docs" / "reference" / "Seminar_Report_Format_2526.docx"
NAME = "Seminar_Report_Manthan_Sankpal"
META = dict(title="AI-Based Prediction of Water Demand and Electricity Consumption", student="Mr. Manthan Sankpal",
            prn="125M1H064", guide="Prof. Dr. Anjana Arakerimath", program="Master of Computer Applications (MCA)",
            academic_year="2026-27", place="Pune", college="Pimpri Chinchwad College of Engineering",
            department="Department of Master of Computer Application")
NAMES = {"seasonal_naive": "Seasonal naive", "sarima": "SARIMA", "ridge": "Ridge", "random_forest": "Random Forest",
         "xgboost": "XGBoost", "lstm": "LSTM", "gru": "GRU", "cnn_lstm": "CNN-LSTM"}
MODELS = list(NAMES)


# ----------------------------------------------------------------------------------------------- data sources
def _load():
    j = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))  # noqa: E731
    y = lambda p: yaml.safe_load((ROOT / p).read_text(encoding="utf-8"))  # noqa: E731
    return {"m": j("results/metrics.json"), "a": j("results/anomaly.json"), "o": j("results/optimisation.json"),
            "e": j("results/eda_summary.json"), "c": y("config/config.yaml"), "f": y("report/facts.yaml")}


DATA = _load()
REFS = {r["key"]: r for r in yaml.safe_load((HERE / "references.yaml").read_text(encoding="utf-8"))}
REG = yaml.safe_load((HERE / "figures.yaml").read_text(encoding="utf-8"))
EQS = yaml.safe_load((HERE / "equations.yaml").read_text(encoding="utf-8"))


def lookup(prefix: str, path: str):
    if prefix == "f":
        return DATA["f"][path]["value"]
    parts = path.split(".")
    if prefix == "m" and "SEL" in parts:
        sel = DATA["m"][parts[0]][parts[1]]["selected"]["model"]
        parts = [sel if p == "SEL" else p for p in parts]
    cur = DATA[prefix]
    for p in parts:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    return cur


def fmt(v, spec: str | None) -> str:
    if spec is None:
        return str(v)
    if spec == "name":
        return NAMES.get(v, str(v))
    if spec == "date":
        d = datetime.fromisoformat(str(v)[:19]) if len(str(v)) > 10 else date.fromisoformat(str(v))
        return f"{d.day} {d:%B %Y}"
    if spec == "len":
        return str(len(v))
    if spec == "p":
        return "p < 0.001" if v < 0.001 else f"p = {v:.3f}"
    if spec == "int":
        return f"{int(round(v)):,}"
    if spec == "list":  # [24, 48, 168] -> "24, 48 and 168"
        v = [str(x) for x in v]
        return v[0] if len(v) == 1 else ", ".join(v[:-1]) + " and " + v[-1]
    return format(v, spec)


# ----------------------------------------------------------------------------------------------- parsing
@dataclass
class Chapter:
    title: str
    blocks: list = field(default_factory=list)  # (kind, payload)
    number: int = 0


def parse(text: str) -> tuple[str, list]:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    title, blocks, buf = "", [], []

    def flush():
        if not buf:
            return
        lines = [ln.rstrip() for ln in buf]
        if all(re.match(r"^- ", ln) or ln.startswith("  ") for ln in lines) and lines[0].startswith("- "):
            items = []
            for ln in lines:
                items.append(ln[2:]) if ln.startswith("- ") else items.__setitem__(-1, items[-1] + " " + ln.strip())
            blocks.append(("bullets", items))
        elif re.match(r"^\d+\. ", lines[0]):
            items = []
            for ln in lines:
                m = re.match(r"^\d+\. (.*)", ln)
                items.append(m.group(1)) if m else items.__setitem__(-1, items[-1] + " " + ln.strip())
            blocks.append(("numbered", items))
        else:
            blocks.append(("para", " ".join(ln.strip() for ln in lines)))
        buf.clear()

    for ln in text.splitlines():
        s = ln.strip()
        m = re.fullmatch(r"\[\[(FIG|TAB|EQ):(\w+)\]\]", s)
        if s.startswith("# "):
            flush(); title = s[2:].strip()
        elif s.startswith("### "):
            flush(); blocks.append(("sub", s[4:].strip()))
        elif s.startswith("## "):
            flush(); blocks.append(("section", s[3:].strip()))
        elif m:
            flush(); blocks.append((m.group(1).lower(), m.group(2)))
        elif not s:
            flush()
        else:
            buf.append(ln)
    flush()
    return title, blocks


def parse_front(text: str) -> dict:
    """ch0_front.md: '# Abstract', '# Acknowledgement', '# Nomenclature' parts; returns {part: blocks}."""
    parts, cur = {}, None
    for chunk in re.split(r"(?m)^# ", re.sub(r"<!--.*?-->", "", text, flags=re.S)):
        if not chunk.strip():
            continue
        head, _, body = chunk.partition("\n")
        parts[head.strip().lower()] = parse("# x\n" + body)[1]
    return parts


# ----------------------------------------------------------------------------------------------- resolution
class Resolver:
    def __init__(self, final: bool):
        self.final, self.problems, self.confirms = final, [], []
        self.cites: list[str] = []
        self.labels: dict[str, str] = {}

    def cite_order(self, text: str):
        for grp in re.findall(r"\[@([^\]]+)\]", text):
            for k in (x.strip().lstrip("@") for x in grp.split(";")):
                if k not in self.cites:
                    self.cites.append(k)

    def text(self, raw: str) -> str:
        def tok(m):
            kind, path, spec = m.group(1), m.group(2), m.group(3)
            if kind in ("fig", "tab", "eq"):
                lab = self.labels.get(path)
                if lab is None:
                    return self._bad(f"unknown {kind} '{path}'")
                return {"fig": f"Figure {lab}", "tab": f"Table {lab}", "eq": f"({lab})"}[kind]
            try:
                return fmt(lookup(kind, path), spec)
            except (KeyError, IndexError, TypeError, ValueError) as e:
                return self._bad(f"{{{{{kind}:{path}}}}} ({type(e).__name__})")

        out = re.sub(r"\{\{(\w+):([^}|]+)(?:\|([^}]+))?\}\}", tok, raw)

        def cite(m):
            nums = []
            for k in (x.strip().lstrip("@") for x in m.group(1).split(";")):
                r = REFS.get(k)
                if r is None or r.get("status") != "verified":
                    return self._bad(f"citation '{k}' missing or not verified")
                nums.append(f"[{self.cites.index(k) + 1}]")
            return ", ".join(nums)
        out = re.sub(r"\[@([^\]]+)\]", cite, out)
        for c in re.findall(r"\[\[CONFIRM:\s*(.*?)\]\]", out):
            if c not in self.confirms:
                self.confirms.append(c)
        if self.final and "[[CONFIRM" in out:
            self.problems.append(f"CONFIRM marker in final mode: {out[:80]}")
        return out

    def _bad(self, msg):
        self.problems.append(msg)
        return f"[[UNRESOLVED: {msg}]]"

    def segs(self, raw: str):
        text = self.text(raw)
        out = []
        for part in re.split(r"(\[\[(?:CONFIRM|UNRESOLVED):.*?\]\]|\*\*.+?\*\*|(?<!\*)\*(?!\*).+?\*|_\{.+?\}|\^\{.+?\})", text):
            if not part:
                continue
            if part.startswith("[["):
                out.append((part, {"highlight": True}))
            elif part.startswith("**"):
                out.append((part[2:-2], {"bold": True}))
            elif part.startswith("*"):
                out.append((part[1:-1], {"italic": True}))
            elif part.startswith("_{"):
                out.append((part[2:-1], {"sub": True}))
            elif part.startswith("^{"):
                out.append((part[2:-1], {"superscript": True}))
            else:
                out.append((part, {}))
        return out

    def plain(self, raw: str) -> str:
        return "".join(t for t, _ in self.segs(raw))


# ----------------------------------------------------------------------------------------------- generated tables
def metrics_table(R):
    """One table for both horizons: MAE and MAPE per resource; * marks the model selected on validation."""
    m = DATA["m"]
    header = ["Model", "D1 elec. MAE", "D1 elec. MAPE", "D1 water MAE", "D1 water MAPE",
              "W1 elec. MAE", "W1 elec. MAPE", "W1 water MAE", "W1 water MAPE"]
    rows = []
    for k in MODELS:
        row = [NAMES[k]]
        for h in ("d1", "w1"):
            for res in ("electricity", "water"):
                t = m[res][h]["test"][k]
                star = "*" if m[res][h]["selected"]["model"] == k else ""
                dec = 3 if t["mae"] < 10 else 2
                row += [f"{t['mae']:.{dec}f}{star}", f"{t['mape']:.1f}"]
        rows.append(row)
    return header, rows, [24.6] + [16.0] * 8


def anomaly_table(R):
    a = DATA["a"]
    header = ["Resource and method", "Detected", "Recall", "Precision (chance)", "False alarms / week", "Median delay"]
    rows = []
    for res, lab in (("water", "Water (real leaks)"), ("electricity", "Electricity (INJECTED)")):
        for meth, mname in (("residual_zscore", "residual z-score"), ("isolation_forest", "Isolation Forest")):
            t = a[res][meth]["test"]
            d = t["median_delay_hours"]
            rows.append([f"{lab}, {mname}", f"{t['n_detected']} of {t['n_labels']}", f"{t['recall']:.2f}",
                         f"{t['precision']:.2f} ({t['chance_precision']:.2f})", f"{t['false_alarms_per_week']:.2f}",
                         "-" if d is None else f"{d:.1f} h"])
    return header, rows, [64, 18, 14, 21, 18, 17.6]


GENERATORS = {"metrics_table": metrics_table, "anomaly_table": anomaly_table}


# ----------------------------------------------------------------------------------------------- references (IEEE)
MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]


def _authors(a):
    """IEEE author list for up to six authors (longer lists are shortened to 'First Author et al.' in ieee())."""
    if len(a) == 1:
        return a[0]
    if len(a) == 2:
        return f"{a[0]} and {a[1]}"
    return ", ".join(a[:-1]) + ", and " + a[-1]


def ieee(r) -> list:
    authors = r["authors"]
    au = f"{authors[0]} et al." if ("et al." in authors or len(authors) > 6) else _authors(authors)
    pages = str(r.get("pages", "")).replace("-", "–")
    doi = f", doi: {r['doi']}." if r.get("doi") else "."
    t, title, venue, year = r["type"], r["title"], r.get("venue", ""), r.get("year", "")
    if t == "journal":
        loc = ", ".join(x for x in [f"vol. {r['volume']}" if r.get("volume") else "", f"no. {r['issue']}" if r.get("issue") else "",
                                    (f"Art. no. {pages}" if pages and not "–" in pages else f"pp. {pages}") if pages else ""] if x)
        return [(f"{au}, “{title},” ", {}), (venue, {"italic": True}), (f", {loc}, {year}{doi}", {})]
    if t == "conference":
        tail = ", ".join(x for x in [r.get("address", ""), str(year), f"pp. {pages}" if pages else ""] if x)
        return [(f"{au}, “{title},” in ", {}), (venue, {"italic": True}), (f", {tail}{doi}", {})]
    if t == "book":
        return [(f"{au}, ", {}), (title, {"italic": True}),
                (f", {r['edition']} ed. {r['address']}: {r['publisher']}, {year}.", {})]
    if t == "dataset":
        ver = f", version {r['version']}" if r.get("version") else ""
        return [(f"{au}, “{title},” ", {}), (venue, {"italic": True}),
                (f"{ver}, {year}. [Online]. Available: {r['url']}{doi}", {})]
    if t == "report":
        return [(f"{au}, “{title},” {r['institution']}, {r['address']}, {r['series']}, {r.get('month', '')} {year}. "
                 f"[Online]. Available: {r['url']}", {})]
    if t == "web":
        d = date.fromisoformat(str(r["accessed"]))
        return [(f"{au}, “{title}.” {venue}. [Online]. Available: {r['url']} "
                 f"(accessed {MONTHS[d.month - 1]} {d.day}, {d.year}).", {})]
    raise ValueError(f"unknown reference type {t}")


# ----------------------------------------------------------------------------------------------- document model
def load_content():
    front = parse_front((CONTENT / "ch0_front.md").read_text(encoding="utf-8"))
    chapters = []
    for i, p in enumerate(sorted(CONTENT.glob("ch[1-9]_*.md")), 1):
        title, blocks = parse(p.read_text(encoding="utf-8"))
        chapters.append(Chapter(title, blocks, i))
    return front, chapters


def first_pass(R, front, chapters):
    """Numbers for sections, figures, tables and equations; citation order; lists for the front matter."""
    toc, lof, lot = [], [], []
    for part in ("abstract", "acknowledgement", "nomenclature"):
        for kind, payload in front.get(part, []):
            for t in (payload if isinstance(payload, list) else [payload]):
                R.cite_order(t)
    for ch in chapters:
        toc.append(("chapter", ch.number, ch.title))
        sec = sub = nfig = ntab = neq = 0
        ch.numbered = []
        for kind, payload in ch.blocks:
            if kind == "section":
                sec += 1; sub = 0
                num = f"{ch.number}.{sec}"
                toc.append(("section", num, payload))
                ch.numbered.append((kind, num, payload))
                continue
            if kind == "sub":
                sub += 1
                ch.numbered.append((kind, f"{ch.number}.{sec}.{sub}", payload))
                continue
            if kind == "fig":
                nfig += 1; R.labels[payload] = f"{ch.number}.{nfig}"
                f = REG["figures"][payload]
                R.cite_order(f["caption"]); R.cite_order(f.get("legend", ""))
                lof.append(payload)
            elif kind == "tab":
                ntab += 1; R.labels[payload] = f"{ch.number}.{ntab}"
                t = REG["tables"][payload]
                R.cite_order(t["caption"])
                for row in t.get("rows", []):
                    for cell in row:
                        R.cite_order(cell)
                lot.append(payload)
            elif kind == "eq":
                neq += 1; R.labels[payload] = f"{ch.number}.{neq}"
            else:
                for t in (payload if isinstance(payload, list) else [payload]):
                    R.cite_order(t)
            ch.numbered.append((kind, None, payload))
    return toc, lof, lot


def build(R, front, chapters, toc, lof, lot, pages: dict, path: Path) -> Path:
    pg = lambda k: pages.get(k, "?")  # noqa: E731
    doc = F.load_base(TEMPLATE, META)
    F.new_section(doc, META, "lowerRoman", 1)
    F.front_title(doc, "Abstract")
    for kind, p in front["abstract"]:
        if kind == "para" and p.startswith("Keywords:"):
            F.body_para(doc, [("Keywords: ", {"bold": True}), *R.segs(p[len("Keywords:"):].strip())], indent_first=False)
        elif kind == "para":
            F.body_para(doc, R.segs(p))
    F.front_title(doc, "Acknowledgement", new_page=True)
    for kind, p in front["acknowledgement"]:
        F.body_para(doc, R.segs(p))
    F.front_title(doc, "Table of Contents", new_page=True)
    for key, label in (("abs", "Abstract"), ("ack", "Acknowledgement"), ("lof", "List of Figures"),
                       ("lot", "List of Tables"), ("nom", "Nomenclature")):
        F.toc_line(doc, label, pg(key))
    for kind, num, title in toc:
        if kind == "chapter":
            F.toc_line(doc, f"Chapter {num}  {title}", pg(f"ch{num}"), bold=True)
        else:
            F.toc_line(doc, f"{num} {title}", pg(f"s{num}"), level=1)
    F.toc_line(doc, "References", pg("ref"), bold=True)
    F.front_title(doc, "List of Figures", new_page=True)
    for fid in lof:
        F.toc_line(doc, f"Figure {R.labels[fid]}  {R.plain(REG['figures'][fid]['caption'])}", pg(f"fig:{fid}"))
    F.front_title(doc, "List of Tables", new_page=True)
    for tid in lot:
        F.toc_line(doc, f"Table {R.labels[tid]}  {R.plain(REG['tables'][tid]['caption'])}", pg(f"tab:{tid}"))
    F.front_title(doc, "Nomenclature", new_page=True)
    for kind, p in front["nomenclature"]:
        if kind in ("sub", "section"):
            F.group_heading(doc, p)
        elif kind == "bullets":
            for item in p:
                term, _, meaning = item.partition(": ")
                F.term_line(doc, R.segs(term), R.segs(meaning))

    F.new_section(doc, META, "decimal", 1)
    for i, ch in enumerate(chapters):
        F.chapter_title(doc, ch.number, ch.title, new_page=i > 0)
        for kind, num, payload in ch.numbered:
            if kind == "section":
                F.section_heading(doc, num, payload)
            elif kind == "sub":
                F.subheading(doc, num, payload)
            elif kind == "para":
                F.body_para(doc, R.segs(payload))
            elif kind in ("bullets", "numbered"):
                F.bullet_list(doc, [R.segs(x) for x in payload], numbered=kind == "numbered")
            elif kind == "fig":
                f = REG["figures"][payload]
                F.figure(doc, ROOT / f["file"], R.labels[payload], R.plain(f["caption"]), f.get("width_mm", 130),
                         R.plain(f["legend"]) if f.get("legend") else None)
            elif kind == "tab":
                t = REG["tables"][payload]
                if "generator" in t:
                    header, rows, widths = GENERATORS[t["generator"]](R, **t.get("args", {}))
                else:
                    header, rows, widths = t["header"], [[R.plain(c) for c in row] for row in t["rows"]], t["widths"]
                F.table(doc, R.labels[payload], R.plain(t["caption"]), header, rows, widths,
                        font_pt=t.get("font_pt", 10), legend=R.plain(t["legend"]) if t.get("legend") else None)
            elif kind == "eq":
                F.equation(doc, [(s[0], s[1] or {}) for s in EQS[payload]], R.labels[payload])
    F.front_title(doc, "References", new_page=True)
    for n, key in enumerate(R.cites, 1):
        F.reference(doc, n, ieee(REFS[key]))
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    return path


def map_entries(chapters, toc, lof, lot, R):
    e = [dict(key="abs", needle="ABSTRACT", zone="front"), dict(key="ack", needle="ACKNOWLEDGEMENT", zone="front"),
         dict(key="lof", needle="LIST OF FIGURES Figure", zone="front"), dict(key="lot", needle="LIST OF TABLES Table", zone="front"),
         dict(key="nom", needle="NOMENCLATURE Abbreviations", zone="front"), dict(key="ref", needle="REFERENCES [1]", zone="body")]
    for kind, num, title in toc:
        if kind == "chapter":
            e.append(dict(key=f"ch{num}", needle=f"CHAPTER {num} {title.upper()}", zone="body"))
        else:
            e.append(dict(key=f"s{num}", needle=f"{num} {title.upper()}", zone="body"))
    e += [dict(key=f"fig:{f}", needle=f"Figure {R.labels[f]}:", zone="body") for f in lof]
    e += [dict(key=f"tab:{t}", needle=f"Table {R.labels[t]}:", zone="body") for t in lot]
    return e


def word_counts(R, front, chapters) -> dict:
    count = lambda s: len(re.findall(r"\S+", R.plain(s)))  # noqa: E731
    out = {"Abstract": sum(count(p) for k, p in front["abstract"] if k == "para" and not p.startswith("Keywords:")),
           "Acknowledgement": sum(count(p) for k, p in front["acknowledgement"] if k == "para")}
    for ch in chapters:
        n = 0
        for kind, payload in ch.blocks:
            if kind == "para":
                n += count(payload)
            elif kind in ("bullets", "numbered"):
                n += sum(count(x) for x in payload)
        out[f"Chapter {ch.number} {ch.title}"] = n
    return out


# ----------------------------------------------------------------------------------------------- checks (R3)
BODY_PAGES = (12, 20, 15)  # min, max, preferred max: option 2 agreed with Manthan on 2026-10-13 (see DECISIONS)
BUDGETS = {1: (450, 550), 2: (300, 400), 3: (900, 1100), 4: (300, 350), 5: (1000, 1200), 6: (700, 900), 7: (350, 450)}
FROZEN_TAG = "v1.0-results-frozen"


def _git(*args):
    import subprocess
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def _grey_image(img) -> bool:
    """True if a pdfplumber image is greyscale: DeviceGray, a grey palette, or RGB pixels with R = G = B."""
    cs = img.get("colorspace") or []
    names = [str(x) for x in cs]
    if any("DeviceGray" in n for n in names):
        return True
    if any("Indexed" in n for n in names):
        pal = cs[-1] if isinstance(cs[-1], bytes) else getattr(cs[-1], "get_data", lambda: b"")()
        return len(pal) % 3 == 0 and all(pal[i] == pal[i + 1] == pal[i + 2] for i in range(0, len(pal), 3))
    try:
        import numpy as np
        a = np.frombuffer(img["stream"].get_data(), dtype=np.uint8)
        a = a[: len(a) // 3 * 3].reshape(-1, 3)
        return bool((a[:, 0] == a[:, 1]).all() and (a[:, 1] == a[:, 2]).all())
    except Exception:  # noqa: BLE001 - undecodable stream: report as not verified
        return False


def check(R, front, chapters, pages, docx: Path, pdf: Path, final: bool) -> bool:
    import pdfplumber
    from docx import Document
    res = []  # (status, check, detail)
    add = lambda ok, name, detail="", warn=False: res.append(("PASS" if ok else ("WARN" if warn else "FAIL"), name, detail))  # noqa: E731
    # 1 page size and margins
    d = Document(str(docx))
    bad = []
    for i, s in enumerate(d.sections):
        for attr, want in (("page_width", F.PAGE_W), ("page_height", F.PAGE_H), ("top_margin", F.MARGINS["top"]),
                           ("bottom_margin", F.MARGINS["bottom"]), ("left_margin", F.MARGINS["left"]), ("right_margin", F.MARGINS["right"])):
            if abs(getattr(s, attr) - want) > 3600:  # 0.1 mm in EMU
                bad.append(f"section {i + 1} {attr}")
    with pdfplumber.open(str(pdf)) as p:
        sizes = {(round(pg.width), round(pg.height)) for pg in p.pages}
        texts = [pg.extract_text() or "" for pg in p.pages]
        labels = [(t.strip().splitlines() or [""])[-1].strip() for t in texts]
        numbered = [i for i, lab in enumerate(labels) if re.fullmatch(r"\d+|[ivxlc]+", lab)]
        fonts = {c["fontname"].split("+")[-1] for pg in p.pages for c in pg.chars}
        img_pages = [(i, len(pg.images)) for i, pg in enumerate(p.pages)]
        not_grey = [f"page {labels[i]}" for i, pg in enumerate(p.pages) if i in numbered for im in pg.images if not _grey_image(im)]
    add(not bad and sizes == {(595, 842)}, "1 A4 page size and margins (25.4 / 37 / 32 / 25.4 mm)",
        "; ".join(bad) or f"PDF page sizes {sorted(sizes)} pt")
    # 2 fonts
    odd = sorted(f for f in fonts if not re.search(r"TimesNewRoman|Times-|LiberationSerif", f))
    add(not odd, "2 fonts are Times New Roman (or Liberation Serif)", ", ".join(odd) or ", ".join(sorted(fonts)))
    # 3 body pages
    total, body = F.page_count(pdf)
    lo, hi, pref = BODY_PAGES
    add(lo <= body <= hi, f"3 body pages between {lo} and {hi} (agreed range)", f"{body} body pages, {total} in total")
    if body > pref:
        add(False, f"3b body pages above the preferred {pref} of the official format", f"{body} pages - confirm with the guide", warn=True)
    # 4 unresolved page numbers or markup
    q = sorted(k for k, v in pages.items() if v == "?")
    full = "\n".join(texts)
    leftovers = sorted(set(re.findall(r"\{\{[^}]*\}\}|\[@[^\]]*\]|\[\[UNRESOLVED[^\]]*\]\]|\[\[(?:FIG|TAB|EQ):[^\]]*\]\]", full)))
    add(not q and not leftovers, "4 no '?' page numbers and no unresolved {{ }}, [@ ] or [[ ]] markup",
        "; ".join(q + leftovers)[:300])
    # 5 CONFIRM markers
    confirms = re.findall(r"\[\[CONFIRM:[^\]]*\]\]", full)
    add(not confirms, "5 no CONFIRM markers", f"{len(confirms)} marker(s): " + "; ".join(R.confirms), warn=not final)
    # 6 at most two images per page
    many = [f"pdf page {i + 1}" for i, n in img_pages if n > 2]
    add(not many, "6 at most two images per page", ", ".join(many))
    # 7 greyscale images on numbered pages (cover and certificate logos come from the official template)
    add(not not_grey, "7 every embedded image on numbered pages is greyscale", ", ".join(not_grey))
    # 8 figures and tables mentioned in the text before they appear
    late = []
    for ch in chapters:
        seen = set()
        for kind, payload in ch.blocks:
            if kind in ("fig", "tab") and payload not in seen:
                late.append(f"{kind} {payload}")
            texts_ = payload if isinstance(payload, list) else [payload] if isinstance(payload, str) else []
            if kind in ("para", "bullets", "numbered"):
                for t in texts_:
                    seen.update(re.findall(r"\{\{(?:fig|tab):(\w+)\}\}", t))
    add(not late, "8 every figure and table is mentioned in the text before it appears", ", ".join(late))
    # 9 references
    unknown = sorted({k for k in R.cites if k not in REFS})
    unverified = sorted({k for k in R.cites if k in REFS and REFS[k].get("status") != "verified"})
    uncited = sorted(set(REFS) - set(R.cites))
    add(not (unknown or unverified or uncited), "9 every citation is in references.yaml, verified, and every reference is cited",
        f"unknown {unknown}, unverified {unverified}, uncited {uncited}" if unknown or unverified or uncited else f"{len(R.cites)} references")
    # 10 objectives match the synopsis
    syn = (ROOT / "docs" / "reference" / "synopsis_content.md").read_text(encoding="utf-8")
    block = syn.split("3. Objectives", 1)[1].split("4. Literature Survey", 1)[0]
    syn_obj = [re.sub(r"\s+", " ", m).strip() for m in re.findall(r"^\d\. (.+?)(?=^\d\. |\Z)", block, re.S | re.M)]
    ch4 = next(c for c in chapters if c.number == 4)
    rep_obj = next((p for k, p in ch4.blocks if k == "numbered"), [])
    add([re.sub(r"\s+", " ", o).strip() for o in rep_obj] == syn_obj, "10 objectives in 4.2 identical to the approved synopsis",
        f"{len(rep_obj)} objectives compared")
    # 11 results come from the frozen tag
    rc_tag, tag_commit = _git("rev-list", "-n", "1", FROZEN_TAG)
    res_commit = DATA["m"].get("git_commit") or ""
    ok_anc = _git("merge-base", "--is-ancestor", res_commit, tag_commit)[0] == 0 if rc_tag == 0 and res_commit else False
    changed = _git("diff", "--name-only", res_commit, tag_commit, "--", "src/wef", "config")[1].split() if ok_anc else ["?"]
    changed = [c for c in changed if not c.startswith("src/wef/viz/")]
    same_files = _git("diff", "--quiet", FROZEN_TAG, "--", "results/metrics.json", "results/anomaly.json",
                      "results/optimisation.json", "results/eda_summary.json")[0] == 0
    add(ok_anc and not changed and same_files, f"11 results are the frozen results of {FROZEN_TAG}",
        f"results commit {res_commit[:7]}, tag {tag_commit[:7]}; code changes in between: {changed or 'none'}; "
        f"results files unchanged since tag: {same_files}")
    # 12 abstract length and chapter budgets
    wc = word_counts(R, front, chapters)
    add(200 <= wc["Abstract"] <= 250, "12 abstract between 200 and 250 words", f"{wc['Abstract']} words")
    for ch in chapters:
        n, (blo, bhi) = wc[f"Chapter {ch.number} {ch.title}"], BUDGETS[ch.number]
        if not (0.8 * blo <= n <= 1.2 * bhi):
            add(False, f"12b chapter {ch.number} within 20 percent of its word budget {blo}-{bhi}", f"{n} words", warn=True)
    lines = [f"Report checks - {datetime.now():%Y-%m-%d %H:%M} - {'final' if final else 'draft'} mode - {pdf.name}", ""]
    lines += [f"{s:4}  {name}" + (f"  [{det}]" if det else "") for s, name, det in res]
    fails = sum(s == "FAIL" for s, _, _ in res)
    lines += ["", f"{fails} failed, {sum(s == 'WARN' for s, _, _ in res)} warnings, {sum(s == 'PASS' for s, _, _ in res)} passed"]
    (OUT / "check_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return fails == 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true", help="fail on CONFIRM markers and unresolved tokens")
    ap.add_argument("--no-pdf", action="store_true", help="skip LibreOffice (single pass, '?' page numbers)")
    ap.add_argument("--check", action="store_true", help="build, then run the format and integrity checks")
    args = ap.parse_args(argv)
    R = Resolver(final=args.final)
    front, chapters = load_content()
    toc, lof, lot = first_pass(R, front, chapters)
    docx = OUT / f"{NAME}.docx"
    build(R, front, chapters, toc, lof, lot, {}, docx)
    pages = {}
    if not args.no_pdf:
        entries = map_entries(chapters, toc, lof, lot, R)
        for _ in range(3):  # converge: page numbers can move the text by a line
            new = F.page_map(F.to_pdf(docx), entries)
            if new == pages:
                break
            pages = new
            R.problems.clear()
            build(R, front, chapters, toc, lof, lot, pages, docx)
        pdf = F.to_pdf(docx)
        total, body = F.page_count(pdf)
        missing = [k for k, v in pages.items() if v == "?"]
        print(f"pages: {total} total, {body} body (numbered 1, 2, ...)" + (f"; page lookup failed for {missing}" if missing else ""))
    wc = word_counts(R, front, chapters)
    lines = [f"{k}: {v} words" for k, v in wc.items()] + [f"Chapters 1-7 total: {sum(v for k, v in wc.items() if k.startswith('Chapter'))} words"]
    (OUT / "word_counts.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"references cited: {len(R.cites)} of {len(REFS)}; uncited: {sorted(set(REFS) - set(R.cites))}")
    if R.confirms:
        print("CONFIRM markers:\n  - " + "\n  - ".join(R.confirms))
    if R.problems:
        print("PROBLEMS:\n  - " + "\n  - ".join(dict.fromkeys(R.problems)))
        if args.final:
            sys.exit(1)
    print(f"built {docx}")
    if args.check:
        if args.no_pdf:
            sys.exit("--check needs the PDF; drop --no-pdf")
        if not check(R, front, chapters, pages, docx, docx.with_suffix(".pdf"), args.final):
            sys.exit(1)


if __name__ == "__main__":
    main()
