# Conclusion

## Conclusion

This seminar built and evaluated a pipeline that forecasts water demand and electricity consumption from public smart-meter data and carries the forecasts into anomaly detection, pump scheduling and dashboards. The six objectives were addressed as follows.

1. The characteristics of the smart-meter data were studied, and a preprocessing pipeline with explicit rules for gaps, daylight saving and outliers was established and tested for look-ahead leakage.
2. Statistical, machine-learning and deep-learning models were compared on identical datasets, splits and forecast origins, with the seasonal-naive forecast as the reference.
3. Next-day and next-week forecasts were produced for both resources; the selected next-day models improved on the baseline by {{m:electricity.d1.test.SEL.skill|.0%}} for electricity and {{m:water.d1.test.SEL.skill|.0%}} for water.
4. Weather, day-of-week and holiday variables were used as predictors; removing the weather inputs changed next-day accuracy little.
5. Abnormal spikes, leakage and wastage were detected from forecast residuals: {{a:water.residual_zscore.test.n_detected}} of {{a:water.residual_zscore.test.n_labels}} labelled test-period leaks and most injected electricity anomalies were found, although false alarms remain too frequent for operational use.
6. Forecasts were visualised through a REST API, a dashboard and a Power BI dataset, and a pumping schedule based on them reduced an illustrative energy cost by {{o:water_pump.summary.selected_forecast.saving_pct_vs_demand_following|.1f}} percent.

The main lesson is that the best model depends on the series: recurrent networks suited the volatile household load, while gradient-boosted trees suited the smooth district demand, and a simple seasonal baseline remained hard to beat at the weekly horizon.

## Limitations

The electricity data came from a single household, which is noisier than a feeder or a city. The leak labels come from a simulated network, and all data are European rather than Indian. Observed weather replaced weather forecasts, the tariff and tank values were illustrative, the electricity anomalies were injected, and the system was not deployed at a live utility.

## Future Scope

Future work should use Indian smart-meter and district data as they become available, and test Transformer-based [@vaswani2017] and probabilistic models that give uncertainty ranges with each forecast. Federated learning would allow models to learn from household data without moving it off the meter, and lightweight models could run at the edge. A digital twin of the distribution network would add leak localisation to leak detection, and explainable methods would help operators trust the forecasts they act on.
