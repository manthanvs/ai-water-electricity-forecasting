# 03 - Final Presentation Instructions

Read `CLAUDE.md` first. Start after the report has passed phase R3 (so slides and report share the same frozen numbers and figures). The seminar guidelines ask for a presentation "utilising audio-visual aids"; this deck, a live demo of the project, and a recorded backup demo cover that.

## A. Outputs

- `presentation/out/Final_Presentation_Manthan_Sankpal.pptx`
- `presentation/out/Final_Presentation_Manthan_Sankpal.pdf` (backup for any machine without PowerPoint)
- `presentation/out/slides/` - one PNG per slide for visual review
- `presentation/out/SPEAKER_SCRIPT.md` - the notes of every slide in one file, with timings
- `presentation/out/DEMO_SCRIPT.md` - live-demo click path and fallback plan
- `presentation/out/VIVA_PREP.md` - likely questions with answers grounded in the results

## B. Assumptions to confirm

- Slot of 10 minutes plus 5 minutes of questions (open question in `CLAUDE.md`). The outline below runs about 10 to 11 minutes; section F says what to cut if the slot is shorter.
- Presented from a college PC or Manthan's laptop over HDMI; the live demo needs Manthan's laptop.

## C. Tooling

- Build with pptxgenjs (Node.js 20 or newer): `presentation/package.json` with pptxgenjs pinned, `presentation/build_deck.js`.
- `presentation/slides.yaml` holds slide text, speaker notes and figure ids. `presentation/make_deck_json.py` resolves the same tokens as the report (`{{m:...}}`, `[@key]`) against the frozen results and `report/references.yaml`, and writes `presentation/deck.json`. `build_deck.js` only renders `deck.json`; it contains no numbers of its own.
- Charts are the colour PNGs from `figures/slides/`, never native PowerPoint charts. Avoid gradient fills and custom shape geometry (pptxgenjs handles them poorly); use solid fills and the built-in rectangle, rounded rectangle and line shapes.
- No images or icons from the internet. Logos come from `assets/` (extracted from the official template); everything else is drawn with shapes or produced by this project.
- Every slide gets speaker notes through `slide.addNotes()`.

## D. Design system

- Layout: 16:9 (`LAYOUT_WIDE`, 13.333 x 7.5 in), white background.
- Colours, taken from the PCCOE logo: primary navy `0B2545` for titles and body text, PCCOE cyan `1AA7D6` for accents and rules, deep blue `13315C` for secondary shapes, light panel `F2F6FA`, highlight yellow `F2C94C` used sparingly (one highlight per slide at most), muted grey `5A6472` for footers and captions.
- Font: Calibri throughout (LibreOffice substitutes the metric-compatible Carlito, so the rendered check matches PowerPoint). Titles 30 pt bold; body 18 to 20 pt; nothing on a slide below 14 pt except the footer (10 pt).
- Every content slide: title top-left with a short cyan rule beneath it; footer left "Manthan Sankpal | PRN 125M1H064 | MCA Seminar (MCA33AE01)"; slide number bottom-right; small PCCOE logo top-right.
- Text rules: one idea per slide; at most 5 bullets; at most about 12 words per bullet; numbers shown as large KPI tiles (rounded rectangle, value 32 pt bold, label 12 pt) rather than inside sentences.
- Figures: placed with `sizing: { type: "contain" }` so the aspect ratio is kept; each figure has a one-line takeaway caption above or beside it, not a description of the axes.

## E. Slide outline (about 10 to 11 minutes)

1. Title (0:20) - title; "Seminar Final Presentation - MCA33AE01"; Mr. Manthan Sankpal, PRN 125M1H064, MCA Semester III; "Guide: Prof. Dr. Anjana Arakerimath, Head of Department"; Department of Master of Computer Application, Pimpri Chinchwad College of Engineering, Pune; 2026-27; large logo.
2. Agenda (0:15) - six items mirroring the report chapters.
3. Why This Matters (0:40) - planning on averages leads to over-pumping, costly peak power and late leak detection; one verified statistic with its citation number.
4. Motivation (0:35) - three panels drawn with shapes: the water-energy link, unused smart-meter data, the cost of reacting late.
5. Literature Survey (0:40) - 2 x 2 grid: statistical, machine learning, deep learning, anomaly detection; each panel one strength and one limitation, with citation numbers.
6. Research Gap and Problem Statement (0:30) - the gap in one sentence; the problem statement in two lines.
7. Objectives (0:30) - the six synopsis objectives in shortened form, numbered.
8. System Architecture (0:45) - fig_architecture; walk through it left to right in the notes.
9. Data (0:40) - three dataset tiles (electricity, water demand, water leaks: source, resolution, period) and fig_eda_profiles.
10. Methodology (0:40) - fig_pipeline; model families listed; the lag rule highlighted as the guard against leakage.
11. Results - Electricity (0:45) - fig_forecast_electricity and three KPI tiles: selected model, its test MAPE for D1, skill versus seasonal naive.
12. Results - Water and Comparison (0:45) - fig_model_comparison (or fig_forecast_water) and KPI tiles for water; one honest sentence about where deep learning did and did not help.
13. Anomaly Detection (0:40) - fig_anomaly_water; tiles for event recall, false alarms per week, median detection delay (real BattLeDIM labels); a small note that electricity anomalies were injected for testing.
14. Optimisation and Cost (0:40) - fig_pump_schedule; tiles for cost saving against demand-following pumping and energy shifted to off-peak; footnote that tariff and tank values are illustrative.
15. Live Demo (1:30) - screenshot of the Streamlit Forecast page with the label "Live demo"; the notes hold the click path; if the demo fails, play the backup video.
16. Conclusion and Future Scope (0:40) - three conclusion bullets mapped to objectives; three future-scope bullets.
17. References (0:10) - the 8 to 10 most important verified references in IEEE style, 12 to 14 pt.
18. Thank You and Questions - contact line with the GitHub repository URL if Manthan wants it shown.

Backup slides after slide 18 (not presented unless asked):
- B1 full test-metrics table (generated from results, 12 pt minimum)
- B2 deep-learning model configuration (window, layers, units, epochs, training time)
- B3 linear-programme formulation for pump scheduling
- B4 data cleaning statistics (gaps, excluded points, outliers)
- B5 limitations in detail

## F. If the slot is shorter

- 8 minutes: merge slides 3 and 4, merge 6 and 7, shorten the demo to 60 seconds.
- 5 minutes: slides 1, 3, 7, 8, 11, 13, 14, 16 and 18 only; demo shown as the recorded video's first 45 seconds.

## G. Speaker notes and script

- 60 to 120 words per slide, written as natural speech in the first person ("Here I compare..."), with the timing at the start of each note.
- Every number in the notes comes from a token, so notes and slides always agree with the report.
- `SPEAKER_SCRIPT.md` collects all notes in order with cumulative time, so Manthan can rehearse with a timer. Recommend three full rehearsals, one of them in front of a friend who asks questions.

## H. Live demo plan (`DEMO_SCRIPT.md`)

Before the session
- Laptop charged; virtual environment and models present; no internet needed.
- Start the API (`flask --app api.app run --port 5000`) and the dashboard (`streamlit run dashboard/app.py`) before the session starts; open the Overview page in the browser at 100 percent zoom (or 125 percent for a large hall).
- Backup video ready: a 90-second screen recording of the same click path, made by Manthan with any screen recorder, saved on the laptop, a USB drive and cloud storage. Name it `Demo_Backup_Manthan_Sankpal.mp4`.

Click path (90 seconds)
1. Overview - point at the latest next-day forecast and the selected model's error.
2. Forecast - switch from electricity to water; show actual versus forecast for a test week.
3. Anomalies - show a labelled BattLeDIM leak and where the detector flagged it.
4. Optimisation - pick a test day; show the pumping plan shifting into off-peak hours and the cost comparison.
5. Return to the slides.

Fallback: if anything fails within 10 seconds, say "I will show the recorded run" and play the video. Do not debug live.

## I. Viva preparation (`VIVA_PREP.md`)

About 30 questions with model answers of three to five sentences, each grounded in this project's numbers (tokens resolved at build time). Group them:
- Concepts: time series components; stationarity; why LSTM and GRU handle long dependencies (gates, cell state); what a CNN layer adds; how XGBoost differs from Random Forest.
- Data: why these datasets; how gaps and daylight-saving changes were handled; what AMI and DMA mean; why L-Town is simulated.
- Evaluation: why chronological splits and rolling origins; what leakage is and how the lag rule prevents it; why MAPE fails near zero and what sMAPE does; why the seasonal-naive baseline matters; what the significance test showed.
- Anomaly detection: robust z-score with median and MAD; how Isolation Forest isolates outliers; precision versus recall trade-off; detection delay.
- Optimisation: the LP's objective and constraints; why perfect-foresight savings are an upper bound; effect of forecast error.
- Implementation: role of Flask versus Streamlit versus Power BI; how a model is served; how this would run for a real utility.
- Indian context and ethics: how this would use national smart-meter data; privacy of household readings; responsible use of AI tools in the project.

Add a "weak points" section with honest answers for the questions most likely to hurt: single household for electricity; simulated network for leaks; observed weather used as forecast; illustrative tariff; deep learning not winning everywhere (if that is the result); European rather than Indian data; points excluded from MAPE.

Add a "papers to know" section: one paragraph each (problem, method, data, main finding) for the five most-cited papers in the report. State at the top that Manthan must read these papers himself; the summaries are a revision aid, not a substitute.

## J. Phases and gates

P1 - Deck content: write `slides.yaml` (text, notes, figure ids) following sections D to G. Gate: print the outline with word counts per slide and total speaking time. Stop.

P2 - Build and visual review: build the deck, convert to PDF with LibreOffice, render every slide to PNG, and look at each one: text overflowing boxes, text below 14 pt, overlapping shapes, figures distorted or too small to read from the back of a room, inconsistent title positions, missing notes. Fix and rebuild until clean. Gate: deck, PDF and slide PNGs written. Stop.

P3 - Script, demo and viva: write `SPEAKER_SCRIPT.md`, `DEMO_SCRIPT.md` and `VIVA_PREP.md`. Gate: every number in all three files traced to a token. Stop and hand over.
