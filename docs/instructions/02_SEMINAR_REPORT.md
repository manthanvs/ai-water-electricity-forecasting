# 02 - Seminar Report Instructions (Final Submission)

Read `CLAUDE.md` first. Start this file only after Phase 11 of the project is complete and the results are frozen (tag `v1.0-results-frozen`). The report reads numbers and figures from the frozen results; it never contains a hand-typed result.

## A. Outputs

- `report/out/Seminar_Report_Manthan_Sankpal.docx` - editable report
- `report/out/Seminar_Report_Manthan_Sankpal.pdf` - for printing and softcopy submission
- `report/out/check_report.txt` - automated format and integrity checks, all passing
- `report/out/STUDENT_REVIEW.md` - what Manthan must personally read, rewrite or confirm before submission
- `report/out/pages/` - one PNG per page used for the visual review

## B. The official format (from Seminar_Report_Format_2526.docx)

Every rule below is already implemented in `report/docx_format.py`. Use its functions; do not restyle paragraphs by hand. If a rule needs a change, change it in that module, rerun `python report/docx_format.py --selftest`, and log the change in `docs/DECISIONS.md`.

1. Hardcopy (spiral bound) and softcopy are both submitted.
2. Length: preferably 12 to 15 pages. Working assumption: Chapter 1 to References (the pages numbered 1, 2, 3...) must be 12 to 15 pages, target 13 to 15. Front matter is numbered i, ii, iii and is not counted. Confirm with the guide (open question in `CLAUDE.md`).
3. Footer on every numbered page: "Pimpri Chinchwad College of Engineering - Department of Master of Computer Application - 2026-27", Times New Roman 10 pt, centred. The page number is centred on the line below (`new_section()` does both). Cover and certificate have no footer.
4. A4 paper. The guideline text says "210X197mm", which is a typo for 210 x 297 mm; use 210 x 297 mm.
5. Margins: top 25.4 mm, bottom 37 mm, right 32 mm, left 25.4 mm (as written in the guideline).
6. Main text: Times New Roman 12 pt, justified, 1.5 line spacing, a blank line's worth of space between paragraphs, and a first-line indent for every paragraph (the "five-space" indent, implemented as 0.5 inch).
7. Chapter titles: bold, 14 pt, ALL CAPITALS, centred. Each chapter starts on a new page.
8. Section headings: left aligned, 12 pt, bold, ALL CAPITALS, with two lines of space before. Sub-headings: left aligned, Title Case, with one line of space before.
9. Illustrations: inside the text, only where pertinent, sharp, clear, black and white. Illustrations downloaded from the internet are not acceptable. At most two per page, ideally one. Figure number and title BELOW the figure in 10 pt. Table number and title ABOVE the table in 10 pt. Legends below the title in 10 pt.
10. Order of contents (the CONTENTS list of the format): Title/Cover Page; Abstract and Keywords; Acknowledgement; Table of Contents, List of Figures, List of Tables and Nomenclature; Introduction (with a section on the organisation of the report); Motivation/Need of the Study; Literature Survey; Problem Statement/Objectives; Details of Study (methodology, analytical demonstration); Discussion on Results/Analysis/Inferences; Conclusion; Bibliography/References.

The cover page and the certificate are not rebuilt. `load_base()` opens the official template, removes the guideline page and the CONTENTS page, fills the placeholders (title, student, PRN, guide, programme, academic year, place) and keeps the PCCOE logos and layout exactly as issued. The cover lists one student only (the template shows four lines for group reports; the extra lines are removed).

## C. Document structure and page budget

Section 1 (no footer): Cover page, Certificate.

Section 2 (lower-case roman page numbers, starting at i), each item on a new page:
- ABSTRACT - 200 to 250 words, one paragraph, then a line "Keywords:" with 5 or 6 keywords (for example: water demand forecasting, electricity load forecasting, smart meters, LSTM, anomaly detection, resource optimisation).
- ACKNOWLEDGEMENT - about 150 words. Thank Prof. Dr. Anjana Arakerimath as Seminar Guide and Head of Department, the Director of PCCOE ([[CONFIRM: Director's name and designation]]), faculty and family. Manthan must personalise this; mark it in STUDENT_REVIEW.md.
- TABLE OF CONTENTS - front-matter items, each chapter (bold) with its numbered sections, and References. Sub-headings are not listed.
- LIST OF FIGURES - "Figure 5.1  caption" with page number.
- LIST OF TABLES - "Table 3.1  caption" with page number.
- NOMENCLATURE - two groups: Abbreviations (alphabetical: AMI, ARIMA, BWDF, CNN, DMA, GRU, LP, LSTM, MAD, MAE, MAPE, ML, NRW, R squared, RMSE, SARIMA, sMAPE, ToD, ...) and Symbols (y_t actual value, y-hat_t forecast, h horizon, n number of points, L_h tank level, p_h pumped volume, k anomaly threshold, ...). Include only terms that actually appear in the text.

Front matter may run onto a second page where needed (TOC usually takes two pages); keep it under about 8 pages.

Section 3 (arabic page numbers, starting at 1). Word budgets are for running text and exclude captions and tables; together with the figures they produce about 14 pages.

CHAPTER 1 - INTRODUCTION (about 450 to 550 words, no figure)
- 1.1 Background - water and electricity as linked civic utilities; the shift from reactive to predictive planning; what smart meters change.
- 1.2 Relevance in the Current Scenario - the Indian context (national smart-meter roll-out, urban water losses, peak-demand pressure on distribution companies). Every statistic needs a verified citation from an official or peer-reviewed source; if none can be verified, drop the statistic rather than keep it uncited. Relate to the department theme only if confirmed.
- 1.3 Purpose of the Study - why this topic was chosen and what the study does: review, implement, compare, and demonstrate a working pipeline.
- 1.4 Organisation of the Report - one paragraph naming each chapter and what it covers (required by the format).

CHAPTER 2 - MOTIVATION AND NEED OF THE STUDY (about 300 to 400 words)
- 2.1 Operational Need - the cost of planning on averages: over-pumping, short-notice power purchase, late leak detection.
- 2.2 The Water-Energy Link - pumping and treatment as electrical loads, so better water forecasts also save electricity.
- 2.3 Unused Smart Meter Data - interval data mainly used for billing.
- 2.4 Expected Benefits - short list: next-day and next-week forecasts, detection of abnormal spikes and wastage, better resource allocation, lower operating cost, sustainability.

CHAPTER 3 - LITERATURE SURVEY (about 900 to 1,100 words, one table)
- 3.1 Statistical Forecasting Methods - ARIMA and SARIMA, exponential smoothing; strengths and the linearity limitation.
- 3.2 Machine Learning Approaches - Random Forest, gradient boosting and XGBoost, support vector regression; dependence on engineered features.
- 3.3 Deep Learning for Time-Series Forecasting - RNN, LSTM, GRU, CNN-LSTM hybrids, a brief note on attention and Transformer models; data needs and interpretability.
- 3.4 Smart Metering and Anomaly Detection - data-quality issues in metering infrastructure; unsupervised detection (Isolation Forest, residual thresholds); leak-detection benchmarks such as BattLeDIM.
- 3.5 Summary of Literature - Table 3.1 with 8 to 10 rows and columns Ref., Method, Data / Domain, Key Finding, Limitation (10 pt; the 5 column widths must add up to 152.6 mm).
- 3.6 Research Gap - most studies treat water or electricity alone and stop at accuracy; this study joins forecasting, anomaly detection, optimisation and dashboards for both resources.
- Cite at least 12 distinct verified sources in this chapter; the synopsis promised a survey of 15 to 20 papers, so the full reference list should contain about 15 to 20 entries.

CHAPTER 4 - PROBLEM STATEMENT AND OBJECTIVES (about 300 to 350 words)
- 4.1 Problem Statement - consistent with the synopsis; one or two paragraphs.
- 4.2 Objectives - the six objectives copied word for word from `docs/reference/synopsis_content.md`, as a numbered list. The check script compares them to the synopsis.
- 4.3 Scope and Assumptions - public datasets (European household and Italian district data, simulated L-Town network for leaks); observed weather used as a perfect forecast; illustrative tariff and tank parameters; CPU-scale models.

CHAPTER 5 - DETAILS OF THE STUDY: METHODOLOGY (about 1,000 to 1,200 words, two figures, one or two tables, equations)
- 5.1 System Architecture - Figure 5.1 (fig_architecture), described layer by layer.
- 5.2 Datasets - Table 5.1 with Dataset, Source, Resolution, Period, Size, Use in this study (values read from the data cards and results).
- 5.3 Data Preprocessing - gaps, daylight-saving handling, outliers, resampling; Figure 5.2 (fig_eda_profiles) with two or three sentences on what the daily and weekly patterns show.
- 5.4 Feature Engineering - calendar, lag and weather features, and the lag rule that prevents look-ahead leakage.
- 5.5 Forecasting Models - one short paragraph per family (baseline, SARIMA, tree ensembles, recurrent networks); the LSTM cell update may be shown as one equation; optional Table 5.2 with key hyper-parameters read from the model cards.
- 5.6 Evaluation Protocol and Metrics - chronological splits and rolling-origin testing; equations for MAE, RMSE and MAPE, numbered (5.1) to (5.3).
- 5.7 Anomaly Detection - robust z-score on forecast residuals (one equation), event merging, Isolation Forest, and how labels were obtained (real BattLeDIM leaks; injected electricity anomalies, stated clearly).
- 5.8 Pump Scheduling Optimisation - the linear programme (objective and constraints as numbered equations) and the evaluation against actual demand.
- 5.9 Implementation - Python, TensorFlow, scikit-learn, XGBoost, statsmodels; Flask API; Streamlit dashboard; Power BI dataset.

CHAPTER 6 - DISCUSSION ON RESULTS (about 700 to 900 words, four or five figures, two or three tables)
- 6.1 Electricity Consumption Forecasting - Table 6.1 (test metrics for all models, D1 and W1, both resources, or split into Table 6.1 for D1 and Table 6.2 for W1); Figure 6.1 (fig_forecast_electricity).
- 6.2 Water Demand Forecasting - Figure 6.2 (fig_forecast_water).
- 6.3 Model Comparison - Figure 6.3 (fig_model_comparison); skill versus the seasonal-naive baseline; the significance test result; the effect of removing weather features. Say plainly where deep learning helped and where it did not.
- 6.4 Anomaly Detection - Table 6.3 (precision, recall, false alarms per week, median delay for each method and resource); Figure 6.4 (fig_anomaly_water). Label electricity results as injected.
- 6.5 Resource Optimisation and Cost Impact - Figure 6.5 (fig_pump_schedule); saving against both baselines and against perfect foresight; state that tariff and tank values are illustrative.
- 6.6 Dashboard and Deployment - Figure 6.6 (fig_dashboard, greyscale screenshot of this project's own Streamlit page); one paragraph on the API and the Power BI dataset.
- 6.7 Key Inferences - four to six bullets, each backed by a number token.

CHAPTER 7 - CONCLUSION (about 350 to 450 words)
- 7.1 Conclusion - answer each of the six objectives in turn with the evidence (this traceability matters in the viva).
- 7.2 Limitations - single household for electricity, simulated network for leaks, European data, perfect-weather assumption, illustrative tariff, no live deployment.
- 7.3 Future Scope - Indian smart-meter data, Transformer-based and probabilistic forecasting, federated learning for privacy, edge deployment on meters, digital twins of distribution networks, explainable AI for operator trust.

REFERENCES - IEEE style, numbered in order of first citation, 15 to 20 entries, every one cited at least once and every one verified.

Total figures: about 8 (two in Chapter 5, five or six in Chapter 6). Total tables: about 5. Never more than two figures on a page.

## D. How the report is built

Content lives in Markdown-like files, one per chapter: `report/content/ch0_front.md` (abstract, keywords, acknowledgement, nomenclature), `ch1_introduction.md` ... `ch7_conclusion.md`. `report/build_report.py` parses them and calls `docx_format.py`. Supported markup (keep it this small):

- `# Title` - chapter title (chapter number comes from file order)
- `## Heading` - numbered section (5.1, 5.2 ...)
- `### Heading` - numbered sub-heading (5.1.1 ...)
- blank-line separated paragraphs; `- item` bullets; `1. item` numbered lists; `**bold**`; `*italic*`
- `[[FIG:fig_id]]` - places a figure; `[[TAB:tab_id]]` - places a table; `[[EQ:eq_id]]` - places a numbered equation
- `{{fig:fig_id}}`, `{{tab:tab_id}}`, `{{eq:eq_id}}` - in-text references, resolved to "Figure 6.1", "Table 3.1", "(5.2)"
- `{{m:dotted.path|format}}` - a number from `results/*.json` (the first path segment selects the file: `m:` reads metrics.json, `a:` reads anomaly.json, `o:` reads optimisation.json, `e:` reads eda_summary.json)
- `[@key]` or `[@key1; @key2]` - citations, rendered as [3] or [3], [7] in order of first appearance
- `[[CONFIRM: ...]]` - rendered with yellow highlight and listed in the build log

`report/figures.yaml` registers every figure (file in `figures/report/`, caption, optional legend, width in mm), every static table (rows written in YAML, for example Table 3.1 and Table 5.1) and every generated table (a Python function name in `build_report.py` that formats rows from the results JSON). `report/equations.yaml` holds equations as segments (see the `equation()` docstring for subscripts; do not use Unicode subscript letters).

Numbering: figures, tables and equations are numbered per chapter in order of appearance (Figure 6.2, Table 6.1, (5.3)). A first pass assigns all numbers before any text is rendered so in-text references resolve.

Two-pass page numbers (proven in the self-test):
1. Build with "?" for every page number in the TOC, List of Figures and List of Tables.
2. Convert to PDF with `to_pdf()`, then call `page_map()` with one entry per TOC line, figure caption and table caption ("CHAPTER 5", "5.3 DATA PREPROCESSING", "Figure 5.1:", "Table 6.1:"); use zone `front` for front-matter items and `body` for everything else.
3. Rebuild with the real numbers, convert again, and assert that no "?" remains and that the page map did not change between the second and a third lookup.

Final file names: `Seminar_Report_Manthan_Sankpal.docx` and `.pdf`.

## E. Bibliography (phase R1, do this before drafting)

1. Start from `report/references.seed.yaml`. Every entry is unverified until checked.
2. For each entry, resolve the DOI through https://doi.org/<doi> or `https://api.crossref.org/works/<doi>`, or open the official page for books, datasets and documentation. Confirm authors, title, venue, volume, issue, pages and year. Correct the entry if needed and set `status: verified`, `verified_on`, and `verified_via`.
3. Add sources to reach 15 to 20 entries, preferring IEEE, Elsevier, ASCE, IWA and Springer journals and conferences from 2016 to 2025, plus the dataset citations and official Indian government sources used in Chapter 1. Add only sources whose abstract (at least) was read and that support the specific sentence that cites them; record in `used_for` which claim each supports.
4. Anything that cannot be verified is listed for the user; it is not cited.
5. IEEE formats:
   - Journal: A. B. Author, C. Author and D. Author, "Title in sentence case," *Journal Name*, vol. X, no. Y, pp. 1-10, Year, doi: 10.xxxx.
   - Conference: A. Author, "Title," in *Proc. Conference Name*, City, Country, Year, pp. 1-10.
   - Book: A. Author, *Title*, Xth ed. City, Country: Publisher, Year.
   - Dataset: A. Author, "Dataset title," Repository, Year. [Online]. Available: URL, doi: ...
   - Web page: Organisation, "Page title." Site. URL (accessed Mon. DD, YYYY).

## F. Writing rules

- Formal academic English, British spelling to match the synopsis (optimise, visualise, behaviour, organisation).
- Third person ("This study", "The selected model"); past tense for what was done, present tense for what the results show.
- Define every abbreviation at first use and list it in the Nomenclature.
- Every literature claim and every statistic is cited; every result is a token.
- Paraphrase sources in new words; no copied sentences and no long quotations. The report will go through a plagiarism checker.
- Mention each figure and table in the text before it appears and say in one or two sentences what it shows.
- Paragraphs of about 80 to 150 words. No promotional wording ("revolutionary", "cutting-edge", "seamless"), no filler sentences, no rhetorical questions.
- Be honest about weak results: if a model lost to the baseline, say so and give the likely reason.

## G. Phases and gates

R1 - Bibliography verified
- Output: `report/references.yaml` and `report/out/reference_verification.md` (one line per entry: key, method used, result).
- Gate: at least 15 verified entries; unverified items listed for the user. Stop.

R2 - Chapter drafts
- Write all content files within the word budgets above, with tokens, citations, figure and table placeholders.
- Gate: run the builder in draft mode (CONFIRM markers allowed); report word counts per chapter. Stop for the user to read the drafts.

R3 - Build and checks
- Build twice for page numbers; run `python report/build_report.py --check`, which writes `check_report.txt` and fails on any of these:
  1. Page size not A4 or margins not as in section B.
  2. Fonts in the PDF other than Times New Roman or its metric-compatible substitute Liberation Serif (check with `pdffonts` or pdfplumber).
  3. Body page count outside 12 to 15 (use `page_count()`).
  4. Any "?" in the TOC or lists; any unresolved `{{`, `[[` or `[@` left in the text.
  5. Any CONFIRM marker (final mode only).
  6. A page with more than two images (pdfplumber `page.images`).
  7. Any embedded image that is not greyscale.
  8. A figure or table not mentioned in the text before it appears.
  9. A cited key missing from references.yaml, an unverified reference, or a reference never cited.
  10. The objectives in 4.2 differ from the synopsis.
  11. The results git commit differs from the frozen tag.
  12. Abstract outside 200 to 250 words (warning for chapter budgets off by more than 20 percent).
- Page budget loop: if over 15 pages, shorten text first in Chapters 3 and 5, then reduce figure widths to no less than 110 mm; never drop the results figures. If under 12, deepen the discussion in Chapter 6 and the limitations in Chapter 7.
- Gate: all checks pass in draft mode. Stop.

R4 - Visual review and student handover
- Render every page to PNG (`pdftoppm -r 80`) and look at each one: heading stranded at the bottom of a page, figure separated from its caption, table overflowing the margin, empty pages, footer present on every numbered page, cover and certificate identical to the template apart from the filled fields.
- Write `report/out/STUDENT_REVIEW.md`: the sections Manthan must rewrite in his own words (Abstract, Acknowledgement, 1.3, 6.7, 7.1), every CONFIRM item with what is needed, the five papers he must read in full before the viva, and the open questions for the guide.
- After Manthan's edits (made in the content files, not in Word), rebuild in final mode; all checks must pass with zero CONFIRM markers.
- If any last cosmetic change is made directly in Word, re-export the PDF from Word and re-run `--check` against that PDF.
