# Problem Statement and Objectives

## Problem Statement

Utility demand is non-linear, seasonal and sensitive to weather and occupancy, so averages and linear models give unreliable short-term estimates; water is over-pumped, reserves are misjudged and leaks stay hidden. The problem addressed is the absence of a unified, data-driven framework that forecasts both water demand and electricity consumption from smart-meter data while flagging abnormal usage.

## Objectives

1. To study the characteristics of smart meter data and establish a reliable preprocessing pipeline.
2. To compare statistical, machine learning and deep learning forecasting models on identical datasets.
3. To forecast next-day and next-week water demand and electricity consumption.
4. To incorporate weather, day-of-week and holiday variables as predictors of demand.
5. To detect abnormal spikes, leakage and wastage from forecast residuals.
6. To visualise forecasts through dashboards that support resource allocation and cost reduction.

The fifth and sixth objectives were extended: detection was evaluated on labelled leaks, and the water forecasts drove a pump-scheduling optimisation.

## Scope and Assumptions

- Public data only: a household in France, district metered areas in Italy and the simulated L-Town network; no Indian utility data were available.
- Observed weather stands in for a forecast; tank, pump and tariff values are illustrative; electricity anomalies are injected.
