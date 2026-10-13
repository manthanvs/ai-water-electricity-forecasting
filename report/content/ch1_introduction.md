# Introduction

## Background

Water and electricity are the two utilities on which urban life depends most directly, and both are supplied by networks that public bodies plan and operate under tight budgets. Much of this planning has been reactive: pumping schedules, reservoir levels and power purchases are set from historical averages and corrected after consumption has already happened. Forecasting reverses this order by estimating demand before it occurs, so that supply can be prepared in advance and the cost of each decision can be weighed beforehand [@hyndman2021].

Smart meters have changed what such forecasting can use. Instead of one reading a month, a utility can record consumption every few minutes or every hour for each customer or each district. Interval data of this kind can describe consumption patterns, predict future demand and support its management [@wang2019smartmeter]. The same data also reveal abnormal behaviour, such as a leak that raises the night flow of a district or an appliance that is left running in a home.

## Relevance in the Current Scenario

India is installing smart meters at national scale. Under the Revamped Distribution Sector Scheme (RDSS), {{f:rdss_sanctioned}} smart electricity meters had been sanctioned in {{f:rdss_states}} States and Union Territories, of which {{f:rdss_installed}} had been installed by {{f:rdss_asof}} [@pib2025smartmeters]. The Ministry of Power notes that these meters provide real-time data, remove estimated readings and help to detect theft [@pib2025smartmeters].

Water supply faces a parallel problem of losses. A World Bank study found that utilities in developing countries covered by its benchmarking network lose {{f:nrw_ibnet}} of the water they produce as non-revenue water, and estimated the true level in the developing world at {{f:nrw_true}} [@kingdom2006nrw]. Both sectors therefore hold growing volumes of interval data and have a clear financial reason to use them for forecasting and for the early detection of losses.

## Purpose of the Study

This topic was chosen because water and electricity are usually planned separately even though they are physically linked, and because the methods and data needed to study both are openly available, which makes the work reproducible. The study has four aims: to review statistical, machine-learning and deep-learning forecasting methods; to implement them on identical public datasets for both resources; to compare them honestly against a simple seasonal baseline; and to demonstrate a working pipeline that turns forecasts into anomaly alerts, a pumping schedule and dashboards.

## Organisation of the Report

The second chapter explains the operational need for short-term forecasting and the link between water and energy. The third chapter reviews the literature on forecasting and on anomaly detection and identifies the research gap. The fourth chapter states the problem, the six objectives and the scope of the study. The fifth chapter describes the system architecture, the datasets, the preprocessing, the models and the evaluation protocol. The sixth chapter presents and discusses the results for forecasting, anomaly detection, optimisation and the dashboard. The seventh chapter concludes the report by answering each objective and outlines limitations and future work.
