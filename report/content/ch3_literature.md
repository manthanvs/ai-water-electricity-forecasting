# Literature Survey

## Statistical Forecasting Methods

Autoregressive integrated moving average (ARIMA) models describe a series through its own past values and past errors, and their seasonal form (SARIMA) adds the same terms at a seasonal lag such as one day or one week [@box2015]. Exponential smoothing and ARIMA remain standard tools for utility demand because they are interpretable, need little data and are cheap to compute, and they perform well when demand is stable and strongly seasonal [@hyndman2021]. Their main limitation is linearity: they combine past values linearly and admit only a few external variables, so irregular events such as heatwaves or holidays are captured poorly. Even the simplest seasonal method, the seasonal-naive forecast that repeats the value observed one season earlier, is a demanding benchmark for short-term demand, and it serves as the reference throughout this study [@hyndman2021].

## Machine Learning Approaches

Tree ensembles learn non-linear relationships between demand and its predictors. A random forest averages many decision trees grown on resampled data with a random choice of features at each split, which makes it robust to noise [@breiman2001]. Gradient boosting builds trees one after another, each correcting the errors of the previous ones; XGBoost made this approach fast and scalable through a sparsity-aware split algorithm and an efficient system design [@chen2016]. For water demand, Antunes et al. compared artificial neural networks (ANN), random forests, support vector machines (SVM) and k-nearest neighbours (k-NN) on data from two Portuguese utilities, studied the influence of weather and seasonality, and validated the forecasts against ARIMA [@antunes2018]. The recurring limitation of these methods is their dependence on feature engineering: they see time only through the lag, calendar and weather variables that the analyst supplies.

## Deep Learning for Time-Series Forecasting

Recurrent neural networks read a sequence step by step and carry an internal state. The long short-term memory (LSTM) network adds gates that control what the state keeps and forgets, which lets it learn long-range dependencies [@hochreiter1997], and the gated recurrent unit (GRU) achieves a similar effect with a simpler gating structure [@cho2014]. Kong et al. showed that an LSTM outperformed competing methods for the short-term load of individual households, where consumption is volatile and hard to predict [@kong2019]. Marino et al. applied LSTM networks to the electricity data of a single household and found that a standard LSTM failed on minute-level data but performed well on hourly data [@marino2016]. Hybrid models place convolutional neural network (CNN) layers that extract local patterns before the recurrent layer; a CNN-GRU model achieved the lowest error among the methods it was compared with on household energy datasets [@sajjad2020].

For water, a GRU network outperformed a conventional neural network and SARIMA for short-term demand [@guo2018], and the Battle of the Water Demand Forecasting (BWDF) compared the methods of many teams on real district metered areas (DMA), stressing evaluation over more than one metric, case and period [@alvisi2025bwdf]. Attention-based architectures such as the Transformer dispense with recurrence altogether [@vaswani2017]. The costs of deep models are their need for data, longer training and reduced interpretability, which matters when a utility must justify its operational decisions.

## Smart Metering and Anomaly Detection

Smart-meter data raise practical problems of volume, privacy and security, and their analysis spans descriptive, predictive and prescriptive tasks [@wang2019smartmeter]. Labelled records of leaks, theft or faults are rarely available, so anomaly detection usually relies on unsupervised methods. Isolation Forest isolates unusual points with random splits instead of modelling normal behaviour, and it runs in linear time [@liu2008]. A simpler alternative, used in this study, thresholds the residuals of a forecasting model and flags hours whose consumption departs from the forecast by more than a chosen number of robust standard deviations. For water networks, the BattLeDIM competition provided a realistic benchmark with labelled leaks on a simulated network and concluded that leak-detection methods still need further development [@vrachimis2022battledim].

## Summary of Literature

{{tab:tab_literature}} summarises the reviewed studies with the method, the data, the main finding and the main limitation of each. Classical models remain strong baselines, tree ensembles and recurrent networks improve accuracy when enough data and good features are available, and anomaly detection is usually evaluated without real labels.

[[TAB:tab_literature]]

## Research Gap

The reviewed studies treat water demand and electrical load separately, and most report forecast accuracy without carrying the forecasts into operation. None of them compares statistical, machine-learning and deep-learning models on the same chronological splits for both resources, and none connects such forecasts to anomaly detection on labelled events, to an optimisation that uses the forecast, and to dashboards. This study addresses that gap by applying one pipeline to both resources and following the forecasts through to alerts, a pumping schedule and decision-support tools.
