# Approved Synopsis (text extract)

Source: docs/reference/Approved_Synopsis_Manthan_Sankpal.docx. This is the synopsis already submitted to the guide. The final report and presentation must stay consistent with it: same title, same six objectives, same problem framing. Where the final work goes beyond it (anomaly evaluation on labelled leaks, pump-scheduling optimisation), present that as an extension of Objective 5 and 6, not a change of scope.

---

Seminar Synopsis Content

1. Abstract

Water and electricity are the two most heavily consumed civic utilities,
yet most municipal bodies and distribution companies still plan supply
using historical averages and manual judgement. This seminar studies how
Artificial Intelligence, applied to smart meter data, can replace that
reactive practice with accurate short-term forecasting. The objective is
to review, implement and compare statistical, machine learning and deep
learning models for predicting next-day and next-week water demand and
electricity consumption. The methodology follows a six-stage pipeline:
acquisition of interval meter data together with weather and calendar
variables; preprocessing and feature engineering; development of ARIMA,
XGBoost and LSTM or GRU models; evaluation using MAE, RMSE, MAPE and R²;
detection of anomalies from forecast residuals; and delivery of results
through Power BI dashboards and a Streamlit prototype served by a Flask
API. Expected outcomes include reliable demand forecasts, early
identification of abnormal spikes, leakage and wastage, and quantified
evidence of where deep learning improves upon classical methods. The
study concludes that predictive analytics enables optimised resource
allocation, reduced operational cost and measurable progress toward
urban sustainability.

2. Introduction

Urban India is under simultaneous pressure from rising water demand and
growing electrical load. Non-revenue water in many Indian cities is
reported in the range of thirty to forty percent, while distribution
companies incur avoidable cost whenever load is under-estimated and
power must be purchased at short notice. Both problems share a common
cause: supply decisions are taken after consumption has occurred rather
than before it. The nationwide deployment of smart meters has changed
the data situation, as utilities now record consumption at
fifteen-minute or hourly intervals. This data, however, is largely
confined to billing and is rarely used for prediction. Time-series
forecasting using machine learning and deep learning offers a direct way
to extract operational value from it, since such models learn
seasonality, weather sensitivity and behavioural patterns that linear
methods cannot capture. The topic was selected because the two resources
are functionally coupled, pumping and treatment of water being
themselves major electrical loads, and because the required tools are
openly available, making the study practically reproducible.

3. Objectives

1. To study the characteristics of smart meter data and establish a
reliable preprocessing pipeline.

2. To compare statistical, machine learning and deep learning
forecasting models on identical datasets.

3. To forecast next-day and next-week water demand and electricity
consumption.

4. To incorporate weather, day-of-week and holiday variables as
predictors of demand.

5. To detect abnormal spikes, leakage and wastage from forecast
residuals.

6. To visualise forecasts through dashboards that support resource
allocation and cost reduction.

4. Literature Survey

The literature reviewed spans peer-reviewed journal articles, IEEE and
Elsevier conference papers and industry documentation published mainly
between 2016 and 2025. Four research streams are evident.

Classical statistical forecasting. Box–Jenkins ARIMA and SARIMA models
and Holt-Winters exponential smoothing remain widely deployed for
utility demand. Hyndman and Athanasopoulos show that these methods are
interpretable, inexpensive to compute and adequate where demand is
stable and strongly seasonal. Their limitation is the assumption of
linearity and the difficulty of admitting several exogenous variables,
so accuracy falls during irregular events such as heatwaves or festival
periods.

Machine learning approaches. Tree-based ensembles consistently
outperform statistical baselines when supplied with engineered features.
XGBoost, introduced by Chen and Guestrin, is the most frequently cited
method in this group, and studies on short-term water demand report that
Random Forest and Support Vector Regression reduce error relative to
ARIMA. The recurring limitation is dependence on manual feature
engineering, since model quality is bounded by the lag and calendar
features the analyst chooses to supply.

Deep learning for time series. The LSTM architecture of Hochreiter and
Schmidhuber, and the later GRU variant, learn temporal dependencies
directly from raw sequences. Kong et al. demonstrated that LSTM networks
outperform conventional methods for short-term residential load
forecasting, particularly at the individual household level where
consumption is volatile. Hybrid CNN-LSTM and attention-based models are
reported to improve multi-step-ahead accuracy further. The trade-offs
identified are large data requirements, longer training time and reduced
interpretability, which matters where utilities must justify operational
decisions.

Smart metering and anomaly detection. Studies on Advanced Metering
Infrastructure highlight practical data problems including missing
intervals, communication gaps, clock drift and privacy restrictions on
household-level readings. Because labelled leakage and theft records are
rarely available, anomaly detection generally relies on unsupervised
methods such as the Isolation Forest of Liu et al., clustering of
consumption profiles, or thresholding of forecast residuals.

Research gap. Existing studies address either water demand or electrical
load, seldom both within a single comparative framework, and most stop
at reported accuracy without extending to a deployable pipeline with
dashboards and alerting. This seminar addresses that gap by treating
forecasting, anomaly detection and operational visualisation as one
integrated study.

5. Problem Statement

Utility demand is non-linear, seasonal at daily, weekly and annual
scales, and sensitive to temperature, humidity and occupancy, so
conventional averaging and linear statistical models produce unreliable
short-term estimates. As a result water is over-pumped, electrical
reserves are misjudged, and leakage remains undetected until it becomes
visible. The problem addressed is the absence of a unified, data-driven
framework that can forecast both water demand and electricity
consumption from smart meter data while simultaneously flagging abnormal
usage. It matters because forecast error translates directly into wasted
resources, higher operational cost and avoidable carbon emissions.

6. Plan of Study

The seminar will be completed in six sequential phases. Phase I
finalises the topic in consultation with the guide and completes a
survey of fifteen to twenty papers drawn from IEEE, Elsevier and reputed
white papers. Phase II collects public smart meter and weather datasets
and builds the preprocessing pipeline covering missing intervals,
outliers and resampling. Phase III engineers lag, rolling-window and
calendar features and establishes ARIMA and XGBoost baselines. Phase IV
develops and tunes LSTM, GRU and CNN-LSTM models in TensorFlow,
evaluated using walk-forward validation. Phase V adds residual-based
anomaly detection and builds the Power BI dashboard with a Streamlit and
Flask prototype. Phase VI consolidates the findings into the seminar
report, verifies it using a plagiarism checker and Grammarly, and
prepares the final presentation.

7. References

[1] S. Hochreiter and J. Schmidhuber, “Long short-term memory,” Neural
Computation, vol. 9, no. 8, pp. 1735–1780, 1997.

[2] W. Kong, Z. Y. Dong, Y. Jia, D. J. Hill, Y. Xu and Y. Zhang,
“Short-term residential load forecasting based on LSTM recurrent neural
network,” IEEE Transactions on Smart Grid, vol. 10, no. 1, pp. 841–851,
2019.

[3] T. Chen and C. Guestrin, “XGBoost: A scalable tree boosting system,”
in Proc. 22nd ACM SIGKDD Int. Conf. Knowledge Discovery and Data Mining,
San Francisco, CA, USA, 2016, pp. 785–794.

[4] F. T. Liu, K. M. Ting and Z.-H. Zhou, “Isolation forest,” in Proc.
8th IEEE Int. Conf. Data Mining (ICDM), Pisa, Italy, 2008, pp. 413–422.

[5] G. E. P. Box, G. M. Jenkins, G. C. Reinsel and G. M. Ljung, Time
Series Analysis: Forecasting and Control, 5th ed. Hoboken, NJ, USA:
Wiley, 2015.

[6] R. J. Hyndman and G. Athanasopoulos, Forecasting: Principles and
Practice, 3rd ed. Melbourne, Australia: OTexts, 2021.

[7] A. Antunes, A. Andrade-Campos, A. Sardinha-Lourenço and M. S.
Oliveira, “Short-term water demand forecasting using machine learning
techniques,” Journal of Hydroinformatics, vol. 20, no. 6, pp. 1343–1366,
2018.

[8] Ministry of Power, Government of India, “Smart Meter National
Programme,” Energy Efficiency Services Limited. [Online]. Available:
https://eeslindia.org

[9] TensorFlow, “Time series forecasting,” TensorFlow Core Tutorials.
[Online]. Available:
https://www.tensorflow.org/tutorials/structured_data/time_series

[10] Microsoft, “Power BI documentation,” Microsoft Learn. [Online].
Available: https://learn.microsoft.com/power-bi/
