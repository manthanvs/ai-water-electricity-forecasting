"""Assemble the softcopy bundle (docs/instructions/04_SUBMISSION_CHECKLIST.md, section D).

    python make_submission.py            needs a final-mode report build that passed --check
    python make_submission.py --draft    same bundle from the current draft; the zip name ends in _DRAFT (checking only)

Put Plagiarism_Report_Manthan_Sankpal.pdf and Demo_Backup_Manthan_Sankpal.mp4 in submission/ first; they are copied
into the bundle when present. Project_Source is the repository at the frozen-results tag (git archive), which holds
no data, no virtual environment and no file over 5 MB.
"""
import shutil
import subprocess
import sys
import tarfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "submission"
NAME = "Seminar_MCA33AE01_125M1H064_Manthan_Sankpal"
TAG = "v1.0-results-frozen"
FILES = {
    "report/out/Seminar_Report_Manthan_Sankpal.pdf": True,
    "report/out/Seminar_Report_Manthan_Sankpal.docx": True,
    "presentation/out/Final_Presentation_Manthan_Sankpal.pptx": True,
    "presentation/out/Final_Presentation_Manthan_Sankpal.pdf": True,
    "docs/reference/Approved_Synopsis_Manthan_Sankpal.docx": True,
    "submission/Plagiarism_Report_Manthan_Sankpal.pdf": False,  # added by Manthan
    "submission/Demo_Backup_Manthan_Sankpal.mp4": False,  # added by Manthan (or share a link if too large)
}


def report_is_final() -> tuple[bool, str]:
    p = ROOT / "report" / "out" / "check_report.txt"
    if not p.exists():
        return False, "no report/out/check_report.txt - run: python report/build_report.py --final --check"
    head, text = p.read_text(encoding="utf-8").splitlines()[0], p.read_text(encoding="utf-8")
    if "final mode" not in head or "\n0 failed" not in text.replace("\r", ""):
        return False, f"last check was not a passing final build ({head.strip()}) - run: python report/build_report.py --final --check"
    return True, head.strip()


def main():
    draft = "--draft" in sys.argv
    ok, msg = report_is_final()
    if not ok and not draft:
        sys.exit(f"STOP: {msg}")
    name = NAME + ("_DRAFT" if draft else "")
    out = SUB / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    missing = []
    for src, required in FILES.items():
        p = ROOT / src
        if p.exists():
            shutil.copy2(p, out / p.name)
        elif required:
            sys.exit(f"STOP: required file missing: {src}")
        else:
            missing.append(p.name)
    tar = subprocess.run(["git", "archive", "--format=tar", "--prefix=Project_Source/", TAG], cwd=ROOT,
                         capture_output=True, check=True).stdout
    with tarfile.open(fileobj=BytesIO(tar)) as t:
        t.extractall(out, filter="data")
    zip_path = shutil.make_archive(str(SUB / name), "zip", root_dir=SUB, base_dir=name)
    size = Path(zip_path).stat().st_size / 1e6
    print(f"{'DRAFT bundle (not for submission)' if draft else 'bundle'}: {out}\nzip: {zip_path} ({size:.1f} MB)")
    print(f"report: {msg}")
    for m in missing:
        print(f"MISSING (Manthan): {m} - put it in submission/ and re-run")


if __name__ == "__main__":
    main()
