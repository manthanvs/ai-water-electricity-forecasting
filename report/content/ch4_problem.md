# Problem Statement and Objectives

## Problem Statement

Utility demand is non-linear, seasonal at daily, weekly and annual scales, and sensitive to temperature, humidity and occupancy, so averages and linear statistical models give unreliable short-term estimates. As a result, water is over-pumped, electrical reserves are misjudged, and leakage remains undetected until it becomes visible. The problem addressed by this seminar is the absence of a unified, data-driven framework that forecasts both water demand and electricity consumption from smart-meter data while flagging abnormal usage. The problem matters because forecast error turns directly into wasted resources, higher operating cost and avoidable emissions.

## Objectives

1. To study the characteristics of smart meter data and establish a reliable preprocessing pipeline.
2. To compare statistical, machine learning and deep learning forecasting models on identical datasets.
3. To forecast next-day and next-week water demand and electricity consumption.
4. To incorporate weather, day-of-week and holiday variables as predictors of demand.
5. To detect abnormal spikes, leakage and wastage from forecast residuals.
6. To visualise forecasts through dashboards that support resource allocation and cost reduction.

The fifth and sixth objectives were extended during the study: anomaly detection was evaluated against labelled leaks, and the water forecasts were used in a pump-scheduling optimisation whose cost effect is reported.

## Scope and Assumptions

- Only public datasets were used: one household in France for electricity, district metered areas in Italy for water demand, and the simulated L-Town network for leaks. No Indian utility data were available.
- Observed weather at the target hour stands in for a weather forecast (a perfect-forecast assumption); an ablation without weather inputs measures its effect.
- The tank, pump and tariff parameters of the optimisation are illustrative assumptions, and costs are reported in relative units.
- Electricity anomalies were injected into a copy of the test data, because no labelled household anomalies exist.
- All models were sized to train on a laptop without a graphics processor.
