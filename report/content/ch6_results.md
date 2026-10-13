# Discussion on Results

## Electricity Consumption Forecasting

{{tab:tab_metrics}} reports the test accuracy of all models for both horizons. For electricity, every model improved on the seasonal-naive baseline. The selected {{m:electricity.d1.selected.model|name}} reached an MAE of {{m:electricity.d1.test.SEL.mae|.3f}} kW (RMSE {{m:electricity.d1.test.SEL.rmse|.3f}} kW), a skill of {{m:electricity.d1.test.SEL.skill|.0%}}, and its advantage over the {{m:electricity.d1.significance.vs|name}} was statistically significant ({{m:electricity.d1.significance.p_value|p}}). Percentage errors stay high ({{m:electricity.d1.test.SEL.mape|.0f}} percent) because a household uses little power at night; {{fig:fig_forecast_electricity}} shows that the model follows the daily rhythm but not individual appliance peaks. For next-week totals, the {{m:electricity.w1.significance.vs|name}} beat the selected {{m:electricity.w1.selected.model|name}} on test, but not significantly ({{m:electricity.w1.significance.p_value|p}}).

[[TAB:tab_metrics]]

[[FIG:fig_forecast_electricity]]

## Water Demand Forecasting

District water demand is much smoother. The selected {{m:water.d1.selected.model|name}} forecast next-day hourly demand with a MAPE of {{m:water.d1.test.SEL.mape|.1f}} percent and a skill of {{m:water.d1.test.SEL.skill|.0%}}, significantly better than the next best model ({{m:water.d1.significance.p_value|p}}), and {{fig:fig_forecast_water}} shows forecasts that track both daily peaks closely. SARIMA was worse than the baseline because it could not follow the drop in demand in late 2022. For next-week water totals the selected {{m:water.w1.selected.model|name}} improved on the baseline by only {{m:water.w1.test.SEL.skill|.0%}}, which was not significant ({{m:water.w1.significance_vs_naive.p_value|p}}). The next-day result held across districts: the same XGBoost configuration beat the baseline in {{m:water.robustness.n_dmas_beating_naive}} of the {{m:water.robustness.dmas|len}} districts, with a median skill of {{m:water.robustness.median_skill|.0%}}.

[[FIG:fig_forecast_water]]

## Model Comparison

{{fig:fig_model_comparison}} compares every model with the baseline. Deep learning helped most where the series is volatile: recurrent networks gave the lowest next-day errors for household electricity, in line with studies of household load [@kong2019; @sajjad2020]. For water, gradient-boosted trees beat the deep models at the next-day horizon (XGBoost {{m:water.d1.test.xgboost.mae|.3f}} L/s against {{m:water.d1.test.gru.mae|.3f}} L/s for the GRU), because smooth district demand is well explained by recent lags and calendar effects and fewer than two years of training data were available. Removing the weather inputs changed next-day errors very little ({{m:electricity.d1.ablation_no_weather.test.xgboost.mae|.3f}} against {{m:electricity.d1.test.xgboost.mae|.3f}} kW for XGBoost on electricity), so recent demand carries most of the information at this horizon.

[[FIG:fig_model_comparison]]

## Anomaly Detection

{{tab:tab_anomaly}} summarises event-level detection. On BattLeDIM, the residual z-score detected {{a:water.residual_zscore.test.n_detected}} of the {{a:water.residual_zscore.test.n_labels}} leaks that began in the test period, with a median delay of {{a:water.residual_zscore.test.median_delay_hours|.0f}} hours and {{a:water.residual_zscore.test.false_alarms_per_week|.2f}} false alarms per week ({{fig:fig_anomaly_water}}). Its precision of {{a:water.residual_zscore.test.precision|.2f}} must be read against the {{a:water.residual_zscore.test.chance_precision|.2f}} that random alarms would reach, because the leaks of 2018 overlap and cover most of the period. Slowly growing leaks are absorbed into the forecast, so some detections of them may be chance. On the injected electricity anomalies, the residual detector found {{a:electricity.recall_by_type_test.residual_zscore.level_shift|.0%}} of the level shifts, {{a:electricity.recall_by_type_test.residual_zscore.drift|.0%}} of the drifts and {{a:electricity.recall_by_type_test.residual_zscore.spike|.0%}} of the spikes, with {{a:electricity.residual_zscore.test.false_alarms_per_week|.1f}} false alarms per week; the Isolation Forest raised fewer alarms but missed most anomalies.

[[TAB:tab_anomaly]]

[[FIG:fig_anomaly_water]]

## Resource Optimisation and Cost Impact

{{fig:fig_pump_schedule}} shows a typical test day: the plan pumps mainly off-peak and fills the tank before the morning peak tariff. Over the {{o:water_pump.n_days}} test days, the plan based on the selected forecast cost {{o:water_pump.summary.selected_forecast.saving_pct_vs_demand_following|.1f}} percent less than demand-following pumping and {{o:water_pump.summary.selected_forecast.saving_pct_vs_level_trigger|.1f}} percent less than the level-triggered rule, against {{o:water_pump.summary.perfect_forecast.saving_pct_vs_demand_following|.1f}} and {{o:water_pump.summary.perfect_forecast.saving_pct_vs_level_trigger|.1f}} percent with perfect foresight and {{o:water_pump.summary.seasonal_naive_forecast.saving_pct_vs_demand_following|.1f}} and {{o:water_pump.summary.seasonal_naive_forecast.saving_pct_vs_level_trigger|.1f}} percent with the seasonal-naive forecast. The better forecast needed less corrective pumping ({{o:water_pump.results.selected_forecast.corrective_m3|int}} against {{o:water_pump.results.seasonal_naive_forecast.corrective_m3|int}} cubic metres); with illustrative parameters, these figures show the mechanism rather than a utility's savings. Electricity peak-day alerts needed a threshold calibrated on validation forecasts, because forecasts are smoother than actual peaks; {{o:electricity_peak_alerts.test_calibrated.alert_days}} alerts then caught {{o:electricity_peak_alerts.test_calibrated.hits}} of {{o:electricity_peak_alerts.test_calibrated.actual_peak_days}} peak days.


## Dashboard and Deployment

{{fig:fig_dashboard}} shows the forecast page of the Streamlit dashboard; other pages show anomalies, the pumping plan, the model comparison and forecasts from uploaded data. It calls the Flask REST API, falls back to local computation if the API is down, and its results are also exported for Power BI.

[[FIG:fig_pump_schedule]]

[[FIG:fig_dashboard]]

## Key Inferences

- Next-day forecasts beat the seasonal-naive baseline for both resources (skill {{m:electricity.d1.test.SEL.skill|.0%}} for electricity, {{m:water.d1.test.SEL.skill|.0%}} for water).
- Deep learning ({{m:electricity.d1.selected.model|name}}) was best for volatile household load, {{m:water.d1.selected.model|name}} for smooth district demand.
- The residual detector found {{a:water.residual_zscore.test.n_detected}} of {{a:water.residual_zscore.test.n_labels}} test leaks, with precision near chance on overlapping leaks.
- Forecast-driven pumping saved {{o:water_pump.summary.selected_forecast.saving_pct_vs_demand_following|.1f}} percent of an illustrative cost, near the {{o:water_pump.summary.perfect_forecast.saving_pct_vs_demand_following|.1f}} percent of perfect foresight.
