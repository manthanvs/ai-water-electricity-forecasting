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
        return "< 0.001" if v < 0.001 else f"{v:.3f}"
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
def metrics_table(R, horizon):
    m = DATA["m"]
    header = ["Model", "Elec. MAE", "Elec. RMSE", "Elec. MAPE", "Water MAE", "Water RMSE", "Water MAPE"]
    rows = []
    for k in MODELS:
        row = [NAMES[k]]
        for res in ("electricity", "water"):
            t = m[res][horizon]["test"][k]
            star = "*" if m[res][horizon]["selected"]["model"] == k else ""
            dec = 3 if t["mae"] < 10 else 2
            row += [f"{t['mae']:.{dec}f}{star}", f"{t['rmse']:.{dec}f}", f"{t['mape']:.1f}"]
        rows.append(row)
    return header, rows, [31, 20.2, 20.2, 20.2, 20.3, 20.3, 20.4]


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
    return header, rows, [46, 19, 16, 27, 22, 22.6]


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
    F.page_break(doc)
    F.front_title(doc, "Acknowledgement")
    for kind, p in front["acknowledgement"]:
        F.body_para(doc, R.segs(p))
    F.page_break(doc)
    F.front_title(doc, "Table of Contents")
    for key, label in (("abs", "Abstract"), ("ack", "Acknowledgement"), ("lof", "List of Figures"),
                       ("lot", "List of Tables"), ("nom", "Nomenclature")):
        F.toc_line(doc, label, pg(key))
    for kind, num, title in toc:
        if kind == "chapter":
            F.toc_line(doc, f"Chapter {num}  {title}", pg(f"ch{num}"), bold=True)
        else:
            F.toc_line(doc, f"{num} {title}", pg(f"s{num}"), level=1)
    F.toc_line(doc, "References", pg("ref"), bold=True)
    F.page_break(doc)
    F.front_title(doc, "List of Figures")
    for fid in lof:
        F.toc_line(doc, f"Figure {R.labels[fid]}  {R.plain(REG['figures'][fid]['caption'])}", pg(f"fig:{fid}"))
    F.page_break(doc)
    F.front_title(doc, "List of Tables")
    for tid in lot:
        F.toc_line(doc, f"Table {R.labels[tid]}  {R.plain(REG['tables'][tid]['caption'])}", pg(f"tab:{tid}"))
    F.page_break(doc)
    F.front_title(doc, "Nomenclature")
    for kind, p in front["nomenclature"]:
        if kind in ("sub", "section"):
            F.body_para(doc, [(p, {"bold": True})], indent_first=False)
        elif kind == "bullets":
            for item in p:
                term, _, meaning = item.partition(": ")
                F.term_line(doc, R.segs(term), R.segs(meaning))

    F.new_section(doc, META, "decimal", 1)
    for i, ch in enumerate(chapters):
        if i:
            F.page_break(doc)
        F.chapter_title(doc, ch.number, ch.title)
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
    F.page_break(doc)
    F.front_title(doc, "References")
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true", help="fail on CONFIRM markers and unresolved tokens")
    ap.add_argument("--no-pdf", action="store_true", help="skip LibreOffice (single pass, '?' page numbers)")
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


if __name__ == "__main__":
    main()
