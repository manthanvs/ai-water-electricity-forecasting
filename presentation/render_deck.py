"""Convert the deck to PDF with LibreOffice, render one PNG per slide and run the automatic part of the P2 review.

    python presentation/render_deck.py

Checks: every slide has speaker notes; no text run below 14 pt except the footer and slide number (10 pt), the
references slide and backup tables (12 pt); slide count matches deck.json. Layout (overflow, overlap, legibility)
still needs a look at presentation/out/slides/*.png.
"""
import json
import re
import sys
import zipfile
from pathlib import Path

import pypdfium2 as pdfium

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "report"))
import docx_format as F  # noqa: E402

OUT = HERE / "out"
PPTX = OUT / "Final_Presentation_Manthan_Sankpal.pptx"


def check(deck) -> list[str]:
    errs = []
    with zipfile.ZipFile(PPTX) as z:
        names = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                       key=lambda n: int(re.search(r"\d+", n).group()))
        if len(names) != len(deck["slides"]):
            errs.append(f"{len(names)} slides in the pptx, {len(deck['slides'])} in deck.json")
        for i, (n, sl) in enumerate(zip(names, deck["slides"]), 1):
            xml = z.read(n).decode("utf-8")
            rels = z.read(n.replace("slides/", "slides/_rels/") + ".rels").decode("utf-8")
            if "notesSlide" not in rels:
                errs.append(f"slide {sl['number']}: no speaker notes")
            small_ok = 1200 if sl["id"] == "references" or any(b["type"] == "table" for b in sl.get("blocks", [])) else 1400
            sizes = list(map(int, re.findall(r'<a:rPr[^>]*\bsz="(\d+)"', xml)))
            for sz in sizes:
                if sz < 1000 or (1000 < sz < small_ok):
                    errs.append(f"slide {sl['number']}: text at {sz / 100:g} pt")
            if sizes.count(1000) > 2:
                errs.append(f"slide {sl['number']}: 10 pt text beyond the footer and number")
    return sorted(set(errs))


def main():
    deck = json.loads((HERE / "deck.json").read_text(encoding="utf-8"))
    errs = check(deck)
    pdf_path = F.to_pdf(PPTX)
    pdf = pdfium.PdfDocument(str(pdf_path))
    out = OUT / "slides"
    out.mkdir(exist_ok=True)
    for old in out.glob("slide_*.png"):
        old.unlink()
    for i in range(len(pdf)):
        pdf[i].render(scale=110 / 72).to_pil().save(out / f"slide_{i + 1:02d}.png")
    print(f"{len(pdf)} slides -> {pdf_path.name} and {out}")
    for e in errs:
        print("FAIL", e)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
