"""Resolve presentation/slides.yaml against the frozen results and write presentation/deck.json.

    python presentation/make_deck_json.py

Tokens and citations are resolved by the report's own resolver (report/build_report.py), so slides, notes and report
share every number and every reference number. The script fails on any unresolved token, a missing figure or a
second highlight on one slide; it warns when a slide breaks the text rules (bullets, words per bullet, note length).
It also renders presentation/*.md.tmpl (speaker script, demo script, viva preparation) into presentation/out/.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "report"))
import build_report as B  # noqa: E402

B.DATA["t"] = json.loads((ROOT / "results" / "tuning.json").read_text(encoding="utf-8"))
OUT = HERE / "out"
WPM = 130  # speaking rate used for the time estimate
MODELS_DEEP = ["lstm", "gru", "cnn_lstm"]


def resolver():
    """Report resolver with the report's citation order, so [n] on a slide is [n] in the report."""
    R = B.Resolver(final=True)
    front, chapters = B.load_content()
    B.first_pass(R, front, chapters)
    return R


def resolve(R, obj):
    if isinstance(obj, str):
        for k in (x.strip().lstrip("@") for g in re.findall(r"\[@([^\]]+)\]", obj) for x in g.split(";")):
            if k not in R.cites:
                R.problems.append(f"citation '{k}' is not cited in the report, so it has no report number")
                return obj
        return R.text(obj)
    if isinstance(obj, list):
        return [resolve(R, x) for x in obj]
    if isinstance(obj, dict):
        return {k: resolve(R, v) for k, v in obj.items()}
    return obj


def deep_config_table(R):
    t, c = B.DATA["t"], B.DATA["c"]["models"]["deep"]
    header = ["Series and horizon", "Model", "Window", "Units", "Layers", "Epochs (best)", "Train time"]
    rows = []
    for task in ("electricity.d1", "electricity.w1", "water.d1", "water.w1"):
        res, h = task.split(".")
        sel = B.DATA["m"][res][h]["selected"]["model"]
        for m in MODELS_DEEP:
            d = t[task][m]
            unit = "hours" if h == "d1" else "days"
            rows.append([f"{res.capitalize()} {h.upper()}", B.NAMES[m] + ("*" if m == sel else ""),
                         f"{c['window'][h]} {unit}", str(d["selected_params"]["units"]), str(d["selected_params"]["layers"]),
                         f"{d['epochs_run']} ({d['best_epoch']})", f"{d['train_seconds']:.1f} s"])
    return header, rows, [3.2, 1.9, 1.6, 1.1, 1.1, 1.8, 1.6]


GENERATORS = {"metrics_table": lambda R: B.metrics_table(R), "deep_config_table": deep_config_table}


def words(s: str) -> int:
    return len(re.findall(r"\S+", s))


def slide_text(s: dict) -> list[str]:
    out = [s.get("title", ""), s.get("subtitle", ""), s.get("takeaway", ""), s.get("footnote", "")] + s.get("lines", [])
    for b in s.get("blocks", []):
        out += b.get("items", []) if b["type"] == "bullets" else []
        out += b.get("lines", []) if b["type"] == "text" else []
        for p in b.get("items", []) if b["type"] == "panels" else []:
            out += [p["head"]] + p["lines"]
    for t in s.get("tiles", []):
        out += [t.get("value", ""), t.get("label", ""), t.get("head", "")] + t.get("lines", [])
    return [x for x in out if x]


def seconds(t: str) -> int:
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def build(spec: dict, R) -> tuple[dict, list[str]]:
    warns, slides = [], []
    for n, raw in enumerate(spec["slides"], 1):
        s = resolve(R, raw)
        sid = s["id"]
        hl = sum(bool(t.get("highlight")) for t in s.get("tiles", [])) + sum(
            bool(p.get("highlight")) for b in s.get("blocks", []) if b["type"] == "panels" for p in b["items"])
        if hl > 1:
            R.problems.append(f"{sid}: {hl} highlights (at most one per slide)")
        for b in s.get("blocks", []):
            if b["type"] == "figure":
                p = ROOT / "figures" / "slides" / f"{b['figure']}.png"
                if not p.exists():
                    R.problems.append(f"{sid}: missing figure {p}")
                    continue
                b["path"] = str(p.relative_to(ROOT)).replace("\\", "/")
                b["px"] = list(Image.open(p).size)
            elif b["type"] == "bullets":
                if len(b["items"]) > 5 and sid not in ("agenda", "objectives"):  # both fixed at six by the outline
                    warns.append(f"{sid}: {len(b['items'])} bullets (max 5)")
                warns += [f"{sid}: bullet of {words(i)} words: {i}" for i in b["items"] if words(i) > 12]
            elif b["type"] == "table" and "generator" in b:
                b["header"], b["rows"], b["widths"] = GENERATORS[b["generator"]](R)
            elif b["type"] == "references":
                b["refs"] = [{"n": R.cites.index(k) + 1, "runs": [{"text": t, "italic": bool(st.get("italic"))} for t, st in B.ieee(B.REFS[k])]}
                             for k in b["keys"]]
                b["refs"].sort(key=lambda r: r["n"])
        nw = words(s["notes"])
        if not 60 <= nw <= 120:
            warns.append(f"{sid}: notes have {nw} words (60-120)")
        s["notes"] = (f"({s['time']}) " if s.get("time") else "(backup slide) " if s.get("backup") else "") + s["notes"]
        s["number"] = s.get("backup") or str(n)
        s["slide_words"] = sum(words(x) for x in slide_text(s))
        s["note_words"] = nw
        slides.append(s)
    deck = {"footer": spec["footer"], "logo_small": "assets/pccoe_logo_small.jpeg", "logo_large": "assets/pccoe_logo_large.jpeg",
            "slides": slides}
    return deck, warns


def outline(deck) -> str:
    lines, plan, est = [], 0, 0
    for s in deck["slides"]:
        t = s.get("time")
        e = s["note_words"] / WPM * 60
        if t:
            plan += seconds(t); est += e
        lines.append(f"{s['number']:>3}  {s['title'][:52]:<52}  slide {s['slide_words']:>3} w  notes {s['note_words']:>3} w"
                     f"  plan {t or '-':>4}  est {int(e) // 60}:{int(e) % 60:02d}")
    lines.append(f"main slides: planned {plan // 60}:{plan % 60:02d}, estimated from notes at {WPM} wpm "
                 f"{int(est) // 60}:{int(est) % 60:02d}")
    return "\n".join(lines)


def render_docs(R, deck) -> list[Path]:
    """presentation/*.md.tmpl -> presentation/out/*.md; {{script}} expands to the speaker notes of the main slides."""
    written = []
    for tmpl in sorted(HERE.glob("*.md.tmpl")):
        text = tmpl.read_text(encoding="utf-8")
        if "{{script}}" in text:
            text = text.replace("{{script}}", speaker_script(deck))
        out = OUT / tmpl.name.removesuffix(".tmpl")
        out.write_text(resolve(R, text), encoding="utf-8")
        written.append(out)
    return written


def speaker_script(deck) -> str:
    parts, cum = [], 0
    for s in deck["slides"]:
        if s.get("backup"):
            continue
        t = s.get("time")
        cum += seconds(t) if t else 0
        head = f"### Slide {s['number']} - {s['title']}"
        timing = f"*{t} on this slide; {cum // 60}:{cum % 60:02d} elapsed at its end*" if t else "*questions*"
        note = re.sub(r"^\(\S+\) ", "", s["notes"])
        parts.append(f"{head}\n\n{timing}\n\n{note}\n")
    return "\n".join(parts)


def main():
    spec = yaml.safe_load((HERE / "slides.yaml").read_text(encoding="utf-8"))
    R = resolver()
    deck, warns = build(spec, R)
    OUT.mkdir(exist_ok=True)
    docs = render_docs(R, deck)
    if R.problems:
        sys.exit("PROBLEMS:\n  - " + "\n  - ".join(dict.fromkeys(R.problems)))
    (HERE / "deck.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8")
    print(outline(deck))
    for w in warns:
        print("WARN", w)
    print(f"wrote {HERE / 'deck.json'}" + "".join(f"\nwrote {d}" for d in docs))


if __name__ == "__main__":
    main()
