# Seminar Final Submission Kit - Claude Code

Topic: AI-Based Prediction of Water Demand and Electricity Consumption
Student: Mr. Manthan Sankpal (PRN 125M1H064), MCA Semester III, Seminar MCA33AE01
Guide: Prof. Dr. Anjana Arakerimath, Head of Department, MCA, PCCOE

This kit turns an empty folder into the complete seminar: the working project, the Seminar Report in the official PCCOE format, and the Final Presentation with demo and viva preparation. Claude Code does the building; Manthan reviews, runs, rewrites the personal sections, and presents.

## 1. What is in the kit

- `CLAUDE.md` - the standing brief Claude Code reads every session: identity details, hard rules, repository layout, phase tracker, open questions.
- `docs/instructions/01_PROJECT_BUILD.md` - the project in twelve gated phases (data, models, anomaly detection, optimisation, API, dashboard, Power BI).
- `docs/instructions/02_SEMINAR_REPORT.md` - the report, built to the official format with numbers pulled automatically from the results.
- `docs/instructions/03_FINAL_PRESENTATION.md` - the deck, speaker script, live-demo plan and viva preparation.
- `docs/instructions/04_SUBMISSION_CHECKLIST.md` - printing, binding, softcopy bundle and presentation-day checks.
- `docs/reference/` - the official report format, the synopsis format, the approved synopsis, and its text.
- `report/docx_format.py` - a tested module that reproduces the official format (cover and certificate are taken from the department's own template, logos included). Run `python report/docx_format.py --selftest` to see a sample.
- `report/references.seed.yaml` - starting bibliography; Claude Code verifies every entry before it can be cited.
- `assets/` - the PCCOE logos extracted from the official template.

## 2. One-time setup on the machine that runs Claude Code

- Python 3.11 (TensorFlow support is the reason for this version)
- Node.js 20 or newer (for building the PowerPoint deck)
- LibreOffice (used headless to convert DOCX and PPTX to PDF and to count pages)
- Git
- Claude Code, with web access allowed (needed to download datasets and verify references)
- Power BI Desktop on Windows (only for the manual Power BI step after Phase 10)

## 3. Start

1. Create a folder named `water-electricity-forecasting` and copy the contents of this kit into it.
2. Open a terminal there and run `git init`.
3. Start Claude Code in that folder.
4. Paste the prompts below one at a time. Each prompt ends at a gate: Claude Code stops and reports. Read the report, answer any questions, then paste the next prompt. Use `/clear` between phases to keep each session focused; `CLAUDE.md` carries the context forward.

## 4. Prompt sequence

Kick-off (Phase 0)

```
Read CLAUDE.md in full, then docs/instructions/01_PROJECT_BUILD.md. In about ten lines, tell me what you will build and list anything in the instructions that looks wrong, risky or impossible on this machine. Then execute Phase 0 only, run its gate checks, update the phase status in CLAUDE.md, and stop.
```

Project phases 1 to 11 (send once per phase, changing the number)

```
Read CLAUDE.md, then execute Phase 1 of docs/instructions/01_PROJECT_BUILD.md. Follow every hard invariant. Run the gate checks, update the phase status in CLAUDE.md, log decisions in docs/DECISIONS.md, and stop with a short report: what was done, key numbers from the results files, files changed, open issues.
```

Extra lines to add for particular phases:
- Phase 1: "If any dataset cannot be downloaded or its licence is unclear, stop and tell me. Do not substitute synthetic data."
- Phase 6: "Before writing results/summary.md, show me the test metrics for every model as a plain list."
- Phase 9: "When done, tell me the exact commands to start the API and the dashboard so I can try them."
- Phase 10: after this phase, Manthan builds the Power BI report with `powerbi/POWERBI_BUILD_GUIDE.md` and saves screenshots in `figures/raw_screenshots/`.
- Phase 11: "Tag the release only after I confirm the numbers look right."

Report

```
Read CLAUDE.md, then docs/instructions/02_SEMINAR_REPORT.md. Execute phase R1 (bibliography verification) only and stop at its gate.
```

```
Execute phase R2 of docs/instructions/02_SEMINAR_REPORT.md: draft every chapter in report/content/ within the word budgets, using tokens for every number and verified citations only. Stop at the gate with word counts per chapter.
```

```
Execute phase R3 of docs/instructions/02_SEMINAR_REPORT.md: build the report with two-pass page numbers, run --check, apply the page-budget loop, and stop at the gate with the check results and the body page count.
```

```
Execute phase R4 of docs/instructions/02_SEMINAR_REPORT.md: render every page, review each one visually, fix layout problems, write report/out/STUDENT_REVIEW.md, and stop.
```

After Manthan has rewritten the personal sections in `report/content/` and cleared the CONFIRM items:

```
Rebuild the report in final mode and run --check. Every check must pass with zero CONFIRM markers. Report the body page count and any warnings.
```

Presentation

```
Read CLAUDE.md, then docs/instructions/03_FINAL_PRESENTATION.md. Execute phase P1 (slides.yaml content) and stop at the gate with the outline, word counts and total speaking time.
```

```
Execute phase P2 of docs/instructions/03_FINAL_PRESENTATION.md: build the deck, render every slide, review each one visually, fix problems, and stop.
```

```
Execute phase P3 of docs/instructions/03_FINAL_PRESENTATION.md: write SPEAKER_SCRIPT.md, DEMO_SCRIPT.md and VIVA_PREP.md, and stop.
```

Submission

```
Read docs/instructions/04_SUBMISSION_CHECKLIST.md. Run every automated check, assemble the submission folder and zip from section D, and give me the list of items that still need me.
```

## 5. What only Manthan can do

- Answer the open questions for the guide (listed in `CLAUDE.md`, section 8) and tell Claude Code the answers.
- Run the pipeline once himself and try the dashboard, so the demo is his own.
- Build the Power BI file from the guide and take the screenshots.
- Read the five key papers named in `STUDENT_REVIEW.md`.
- Rewrite the Abstract, Acknowledgement, Purpose of the Study, Key Inferences and Conclusion in his own words.
- Run the plagiarism check and the grammar pass; feed changes back into the content files.
- Record the backup demo video; rehearse the talk three times.
- Get the certificate signed; print and spiral-bind the report; submit the softcopy.

## 6. Suggested order of work

- Days 1 to 3: Phases 0 to 3 (setup, data, cleaning, features)
- Days 4 to 6: Phases 4 to 6 (all models and evaluation)
- Days 7 to 8: Phases 7 and 8 (anomaly detection, optimisation)
- Days 9 to 10: Phases 9 to 11 (API, dashboard, Power BI, freeze)
- Days 11 to 13: Report R1 to R4 and Manthan's rewrite
- Days 14 to 15: Presentation P1 to P3, rehearsals
- Day 16: plagiarism check, final build, printing, binding, submission

Compress or stretch to the actual deadline; the gates make it safe to pause between any two phases.
