# Power BI build guide

This guide is for building the Power BI report by hand in **Power BI Desktop** (Windows). Claude Code cannot write `.pbix` files, so the project exports a clean star schema and this guide gives every step. Budget about 60-90 minutes.

## 0. Before you start

1. Run the pipeline so the export exists: `python -m wef.cli export-powerbi` (or `python -m wef.cli all`).
2. Check that `powerbi/exports/` has eight CSV files: `fact_consumption`, `fact_forecast`, `fact_anomaly`, `fact_metrics`, `fact_schedule`, `dim_date`, `dim_resource`, `dim_model`.
3. Save your work as `powerbi/water_electricity.pbix`. The `.pbix` file stays on your machine; it is not committed.

What each table holds:

- `fact_consumption`: one row per hour and resource: `timestamp`, `resource`, `actual`, `unit` (kW for electricity, L/s for water), `date`.
- `fact_forecast`: every validation and test forecast of every model: `origin`, `timestamp`, `resource`, `horizon` (d1 = next day hourly, w1 = next week daily), `model`, `step` (0 = first hour or day of the forecast), `split`, `eval_ok` (TRUE when the origin is used in the official scores), `actual`, `forecast`, `date`.
- `fact_anomaly`: detected events (`kind` = detection; `method` = residual_zscore or isolation_forest) and the labels they are scored against (`kind` = label). Electricity labels are INJECTED anomalies; water labels are the BattLeDIM 2018 leak list.
- `fact_metrics`: the official scores, long format: `resource`, `horizon`, `split`, `model`, `metric` (mae, rmse, mape, smape, r2, peak_mae, skill, ...), `value`, `is_selected`.
- `fact_schedule`: pump-scheduling result per water test day and plan (`plan` = selected_forecast, seasonal_naive_forecast, perfect_forecast, demand_following, level_trigger): `cost`, `energy_kwh`, `offpeak_kwh`, `peak_kwh`, `corrective_m3`, `spill_m3`. ILLUSTRATIVE ASSUMPTIONS (tank, pump and tariff are not from a real utility).
- `dim_date` (key `date`), `dim_resource` (key `resource`), `dim_model` (key `model`, with `display_name`, `family`, and one `selected_<resource>_<horizon>` flag per task).

## 1. Import the CSV files

1. Home > Get data > Text/CSV. Pick `fact_consumption.csv` and click **Transform Data** (not Load).
2. In Power Query, set the column types:
   - `timestamp`, `origin`, `alarm`, `start`, `end`: Date/Time. If Power BI shows errors, use right-click > Change Type > Using Locale > Date/Time, English (United States); the files use ISO format `2010-07-01T00:00:00`.
   - `date` (every table): Date.
   - `actual`, `forecast`, `value`, `score`, `cost`, `energy_kwh`, `offpeak_kwh`, `peak_kwh`, `corrective_m3`, `spill_m3`: Decimal number.
   - `step`, `year`, `month`, `day`, `weekday`: Whole number.
   - `eval_ok`, `is_selected`, `is_weekend`, `uses_weather`, `selected_*`: True/False.
3. Home > New Source > Text/CSV for each of the other seven files, with the same type rules.
4. Close & Apply. `fact_forecast` has about 150,000 rows; loading takes under a minute.

## 2. Relationships (Model view)

Delete any relationships Power BI guessed, then create these. All are many-to-one, single cross-filter direction, from the fact (many) to the dimension (one):

- `fact_consumption[date]` to `dim_date[date]`; `fact_consumption[resource]` to `dim_resource[resource]`
- `fact_forecast[date]` to `dim_date[date]`; `fact_forecast[resource]` to `dim_resource[resource]`; `fact_forecast[model]` to `dim_model[model]`
- `fact_anomaly[date]` to `dim_date[date]`; `fact_anomaly[resource]` to `dim_resource[resource]`
- `fact_metrics[resource]` to `dim_resource[resource]`; `fact_metrics[model]` to `dim_model[model]`
- `fact_schedule[date]` to `dim_date[date]`; `fact_schedule[resource]` to `dim_resource[resource]`

Then select `dim_date` > Table tools > **Mark as date table** > column `date`.

The keys are unique in every dimension (the project's tests check this), so every relationship should be accepted as many-to-one.

## 3. Measures (DAX)

Home > Enter data > create an empty table named `Measures`, then add each measure with Modeling > New measure (home table: `Measures`).

```DAX
Total Consumption =
SUMX (
    fact_consumption,
    fact_consumption[actual] * IF ( fact_consumption[resource] = "water", 3.6, 1 )
)
```
Hourly kW summed over hours is kWh; hourly L/s times 3.6 is m3 per hour. Always show it with a resource slicer, because the two units cannot be added.

```DAX
Forecast Error =
AVERAGEX (
    FILTER ( fact_forecast, fact_forecast[eval_ok] && NOT ISBLANK ( fact_forecast[actual] ) ),
    ABS ( fact_forecast[forecast] - fact_forecast[actual] )
)
```
This is the mean absolute error (MAE) of whatever is in the filter context.

```DAX
MAPE =
CALCULATE (
    AVERAGE ( fact_metrics[value] ),
    fact_metrics[metric] = "mape",
    fact_metrics[split] = "test"
)
```
This reads the official test MAPE computed by the pipeline (it excludes near-zero actuals). Do not recompute MAPE in DAX; the numbers would differ from the report.

```DAX
Anomaly Count =
CALCULATE ( COUNTROWS ( fact_anomaly ), fact_anomaly[kind] = "detection" )
```

```DAX
Estimated Saving % =
1
    - DIVIDE (
        CALCULATE ( SUM ( fact_schedule[cost] ), fact_schedule[plan] = "selected_forecast" ),
        CALCULATE ( SUM ( fact_schedule[cost] ), fact_schedule[plan] = "demand_following" )
    )
```
Format it as a percentage. Over all dates it must equal `water_pump.summary.selected_forecast.saving_pct_vs_demand_following` in `results/optimisation.json` (that file gives it in percent). If it does not, a relationship or filter is wrong.

Check values: with resource = water, horizon = d1, split = test and `dim_model[selected_water_d1]` = TRUE, the `MAPE` card must equal `water.d1.test.<selected model>.mape` in `results/metrics.json`.

## 4. Report pages

Use View > Page view > Fit to page, and page size 16:9. Use the same colours as the slides: Format > Theme > Customize current theme > Name and colors, colour 1 `#2A78D6`, colour 2 `#EB6834`, colour 3 `#1BAF7A`, colour 4 `#EDA100`.

### Page 1 - Overview

- Slicer (tile style): `dim_resource[resource]`, single select, default electricity.
- Four cards across the top:
  - `Total Consumption`.
  - `MAPE`, with visual-level filters `fact_metrics[horizon]` = d1 and `fact_metrics[is_selected]` = True. Title it "Test MAPE, selected model (%)".
  - `Anomaly Count`.
  - `Estimated Saving %`. Title it "Pump cost saving (illustrative)"; it is water only.
- Line chart: X axis `dim_date[date]` (date hierarchy off), Y axis `Total Consumption`. Title "Daily consumption".
- Text box: "Electricity: one household, Sceaux, 2006-2010 (UCI). Water: district DMA 3, north-east Italy, 2021-2023 (BWDF). Leak data: BattLeDIM L-Town, simulated network. Electricity anomalies are INJECTED. Tank, pump and tariff are ILLUSTRATIVE ASSUMPTIONS."

### Page 2 - Forecast versus Actual

- Slicers: `dim_resource[resource]` (single), `fact_forecast[horizon]` (single), `dim_model[display_name]` (single, default the selected model), `fact_forecast[split]` = test, and `dim_date[date]` as a "Between" slider set to one test week.
- Visual-level filter on the line chart: `fact_forecast[step]` = 0 when the horizon is w1 (one-day-ahead forecasts, so each day appears once); for d1 leave all steps.
- Line chart: X axis `fact_forecast[timestamp]`; Y axis `Average of actual` and `Average of forecast` (rename them "Actual" and "Forecast").
- Card: `Forecast Error`, titled "MAE in view".
- Clustered bar chart: Y axis `dim_model[display_name]`, X axis `Average of fact_metrics[value]`, filters `fact_metrics[metric]` = mae, `fact_metrics[split]` = test. Title "Test MAE by model". Sort ascending.

### Page 3 - Anomalies and Savings

- Slicer: `dim_resource[resource]`.
- Line chart: X axis `fact_consumption[timestamp]`, Y axis `Average of fact_consumption[actual]`. Set the date slicer to the anomaly test period: water July to December 2018, electricity July to November 2010. Note that the electricity consumption table shows the real series; the injected copy is only in the evaluation.
- Table: `fact_anomaly` columns `kind`, `method`, `type`, `start`, `end`, `score`, `label_source`. Sort by `start`.
- Card: `Anomaly Count`. Use a small clustered column chart of `Anomaly Count` by `fact_anomaly[method]`.
- Clustered column chart: X axis `fact_schedule[plan]`, Y axis `Sum of fact_schedule[cost]`. Title "Pump energy cost by plan, water test period (cost units, illustrative)".
- Card: `Estimated Saving %`.
- Text box: "Electricity anomalies are INJECTED (synthetic) for evaluation. Tank, pump and tariff parameters are ILLUSTRATIVE ASSUMPTIONS, not real utility data."

## 5. Screenshots for the report and slides

1. Show each page full screen: View > Focus mode off, and hide the Filters pane (View > Filters). Use a 1920 x 1080 screen if possible.
2. Press Win + Shift + S, choose Window or Rectangle, and capture the report canvas only (no ribbon).
3. Save as PNG in `figures/raw_screenshots/`:
   - `powerbi_overview.png` (page 1, resource = water)
   - `powerbi_forecast.png` (page 2, water, d1, selected model, one test week)
   - `powerbi_anomalies.png` (page 3, water)
4. Run `python -m wef.cli figures`. It converts these screenshots to the greyscale report versions and the slide versions and registers them as optional figures.

## 6. Checklist

- Eight tables loaded; types set; the 11 relationships created; `dim_date` marked as date table.
- The `Estimated Saving %` and `MAPE` check values in section 3 match the results files.
- The INJECTED and ILLUSTRATIVE ASSUMPTIONS labels are visible on pages 1 and 3.
- Three screenshots saved with the exact file names above.
