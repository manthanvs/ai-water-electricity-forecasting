# Discussion on Results

## Electricity Consumption Forecasting

{{tab:tab_metrics_d1}} reports the test accuracy of all models for next-day forecasts and {{tab:tab_metrics_w1}} for next-week forecasts. For electricity, every model improved on the seasonal-naive baseline, whose next-day MAE was {{m:electricity.d1.test.seasonal_naive.mae|.3f}} kW. The selected {{m:electricity.d1.selected.model|name}} reached {{m:electricity.d1.test.SEL.mae|.3f}} kW, a skill of {{m:electricity.d1.test.SEL.skill|.0%}}, and its advantage over the {{m:electricity.d1.significance.vs|name}} was statistically significant (p = {{m:electricity.d1.significance.p_value|p}}). Percentage errors remain high ({{m:electricity.d1.test.SEL.mape|.0f}} percent) because a single household uses little power at night, so small absolute errors become large percentages. {{fig:fig_forecast_electricity}} shows that the model follows the daily rhythm but cannot anticipate individual appliance peaks.

[[TAB:tab_metrics_d1]]

[[FIG:fig_forecast_electricity]]

For next-week electricity totals, {{m:electricity.w1.selected.model|name}} was selected on validation data with a test MAE of {{m:electricity.w1.test.SEL.mae|.2f}} kWh per day, while the {{m:electricity.w1.significance.vs|name}} reached {{m:electricity.w1.test.lstm.mae|.2f}} on the test period; the difference was not significant (p = {{m:electricity.w1.significance.p_value|p}}).

[[TAB:tab_metrics_w1]]

## Water Demand Forecasting

District water demand is much smoother. The selected {{m:water.d1.selected.model|name}} forecast next-day hourly demand with a MAPE of {{m:water.d1.test.SEL.mape|.1f}} percent and a skill of {{m:water.d1.test.SEL.skill|.0%}}, significantly better than the next best model (p = {{m:water.d1.significance.p_value|p}}). {{fig:fig_forecast_water}} shows forecasts that track both daily peaks closely. SARIMA was worse than the baseline: demand fell to a lower level in late 2022, before the validation period, and a model with fixed parameters cannot follow such a shift. For next-week water totals the gain was small: the selected {{m:water.w1.selected.model|name}} improved on the baseline by only {{m:water.w1.test.SEL.skill|.0%}}, and the difference was not significant (p = {{m:water.w1.significance_vs_naive.p_value|p}}). The next-day result is not specific to one district: the same XGBoost configuration beat the baseline in {{m:water.robustness.n_dmas_beating_naive}} of the {{m:water.robustness.dmas|len}} districts, with a median skill of {{m:water.robustness.median_skill|.0%}}.

[[FIG:fig_forecast_water]]

## Model Comparison

{{fig:fig_model_comparison}} compares every model with the baseline. Deep learning helped most where the series is volatile: the recurrent networks gave the lowest next-day errors for household electricity, in line with studies of household load [@kong2019; @sajjad2020]. For water, gradient-boosted trees beat the deep models at the next-day horizon (XGBoost {{m:water.d1.test.xgboost.mae|.3f}} L/s against {{m:water.d1.test.gru.mae|.3f}} L/s for the GRU), because the smooth district demand is well explained by recent lags and calendar effects, and fewer than two years of training data were available. Removing the weather inputs changed the next-day errors very little ({{m:electricity.d1.ablation_no_weather.test.xgboost.mae|.3f}} against {{m:electricity.d1.test.xgboost.mae|.3f}} kW for XGBoost on electricity), which suggests that recent demand already carries most of the information at this horizon.

[[FIG:fig_model_comparison]]

## Anomaly Detection

{{tab:tab_anomaly}} summarises event-level detection. On BattLeDIM, the residual z-score detected {{a:water.residual_zscore.test.n_detected}} of the {{a:water.residual_zscore.test.n_labels}} leaks that began in the test period, with a median delay of {{a:water.residual_zscore.test.median_delay_hours|.0f}} hours and {{a:water.residual_zscore.test.false_alarms_per_week|.2f}} false alarms per week ({{fig:fig_anomaly_water}}). Its precision of {{a:water.residual_zscore.test.precision|.2f}} must be read against the {{a:water.residual_zscore.test.chance_precision|.2f}} that randomly placed alarms would reach, because the leaks of 2018 overlap and cover most of the period. Abrupt leaks, which change the inflow at once, are the easiest to detect; slowly growing leaks are absorbed into the forecast as its lags adapt, so some detections of them may be chance. On the injected electricity anomalies, the residual detector found {{a:electricity.recall_by_type_test.residual_zscore.level_shift|.0%}} of the level shifts, {{a:electricity.recall_by_type_test.residual_zscore.drift|.0%}} of the drifts and {{a:electricity.recall_by_type_test.residual_zscore.spike|.0%}} of the spikes, at the cost of {{a:electricity.residual_zscore.test.false_alarms_per_week|.1f}} false alarms per week; the Isolation Forest raised fewer alarms but missed most anomalies.

[[TAB:tab_anomaly]]

[[FIG:fig_anomaly_water]]

## Resource Optimisation and Cost Impact

{{fig:fig_pump_schedule}} shows the plan for a typical test day: the linear programme pumps mainly in off-peak hours, fills the tank before the morning peak tariff and keeps the level within its limits under the actual demand. Over the {{o:water_pump.n_days}} test days, the plan based on the selected forecast cost {{o:water_pump.summary.selected_forecast.saving_pct_vs_demand_following|.1f}} percent less than demand-following pumping and {{o:water_pump.summary.selected_forecast.saving_pct_vs_level_trigger|.1f}} percent less than the level-triggered rule. Perfect foresight would save {{o:water_pump.summary.perfect_forecast.saving_pct_vs_demand_following|.1f}} and {{o:water_pump.summary.perfect_forecast.saving_pct_vs_level_trigger|.1f}} percent, and the seasonal-naive forecast {{o:water_pump.summary.seasonal_naive_forecast.saving_pct_vs_demand_following|.1f}} and {{o:water_pump.summary.seasonal_naive_forecast.saving_pct_vs_level_trigger|.1f}} percent, so a better forecast closes part of the gap by needing less corrective pumping ({{o:water_pump.results.selected_forecast.corrective_m3|int}} against {{o:water_pump.results.seasonal_naive_forecast.corrective_m3|int}} cubic metres). Because the tank, pump and tariff are illustrative, these percentages show the mechanism rather than the savings of a particular utility. For electricity, the peak-day rule raised no alerts, since forecasts are smoother than actual peaks; with a threshold calibrated on validation forecasts, {{o:electricity_peak_alerts.test_calibrated.alert_days}} alerts caught {{o:electricity_peak_alerts.test_calibrated.hits}} of the {{o:electricity_peak_alerts.test_calibrated.actual_peak_days}} peak days.

[[FIG:fig_pump_schedule]]

## Dashboard and Deployment

{{fig:fig_dashboard}} shows the forecast page of the Streamlit dashboard, which compares actual demand with any model's forecast for a chosen test window and offers the data for download. Other pages give an overview of both resources, anomaly timelines with labelled leaks, the pumping plan with adjustable tank and pump capacity, the model comparison and a forecast from uploaded readings. The dashboard calls the Flask REST API and computes the same answers locally if the API is unavailable, and the results are also exported as fact and dimension tables for Power BI.

[[FIG:fig_dashboard]]

## Key Inferences

- Next-day forecasts beat the seasonal-naive baseline clearly for both resources, with a skill of {{m:electricity.d1.test.SEL.skill|.0%}} for household electricity and {{m:water.d1.test.SEL.skill|.0%}} for district water demand.
- Deep learning was the most accurate for the volatile household load ({{m:electricity.d1.selected.model|name}}), but not for the smooth district demand, where {{m:water.d1.selected.model|name}} was best.
- Weekly forecasts gained less, and the selected weekly water model was not significantly better than the baseline (p = {{m:water.w1.significance_vs_naive.p_value|p}}).
- The residual detector found {{a:water.residual_zscore.test.n_detected}} of {{a:water.residual_zscore.test.n_labels}} test-period leaks within a median of {{a:water.residual_zscore.test.median_delay_hours|.0f}} hours, but on overlapping leaks its precision was close to chance.
- Forecast-driven pump scheduling saved {{o:water_pump.summary.selected_forecast.saving_pct_vs_demand_following|.1f}} percent of an illustrative energy cost against demand-following pumping, close to the {{o:water_pump.summary.perfect_forecast.saving_pct_vs_demand_following|.1f}} percent possible with perfect foresight.
