# Literature Survey

## Statistical Forecasting Methods

Autoregressive integrated moving average (ARIMA) models describe a series through its own past values and past errors, and seasonal ARIMA (SARIMA) adds the same terms at a seasonal lag such as one day or one week [@box2015]. Together with exponential smoothing they remain standard tools for utility demand because they are interpretable and cheap to compute, and they perform well when demand is stable and strongly seasonal [@hyndman2021]. Their limitation is linearity and the small number of external variables they admit, so heatwaves and holidays are captured poorly. Even the seasonal-naive forecast, which repeats the value observed one season earlier, is a demanding benchmark, and it serves as the reference throughout this study [@hyndman2021].

## Machine Learning Approaches

A random forest averages many decision trees grown on resampled data [@breiman2001], while gradient boosting builds trees that each correct the errors of the previous ones; XGBoost made boosting fast and scalable [@chen2016]. For water demand, Antunes et al. compared artificial neural networks (ANN), random forests, support vector machines (SVM) and k-nearest neighbours (k-NN) on data from two Portuguese utilities, studied the effect of weather and seasonality, and validated the forecasts against ARIMA [@antunes2018]. These methods capture non-linear effects, but they see time only through the lag, calendar and weather features that the analyst supplies.

## Deep Learning for Time-Series Forecasting

The long short-term memory (LSTM) network adds gates to a recurrent network so that it can keep information over long spans [@hochreiter1997], and the gated recurrent unit (GRU) achieves a similar effect with a simpler structure [@cho2014]. An LSTM outperformed competing methods for the volatile load of individual households [@kong2019]; on single-household data, a standard LSTM failed at minute resolution but worked well on hourly data [@marino2016]; and a hybrid of convolutional neural network (CNN) and GRU layers gave the lowest error among the compared methods on household energy data [@sajjad2020]. For water, a GRU network outperformed a conventional neural network and SARIMA [@guo2018], and the Battle of the Water Demand Forecasting (BWDF) compared the methods of many teams on real district metered areas (DMA), stressing evaluation over more than one metric and period [@alvisi2025bwdf]. Attention-based Transformers remove recurrence altogether [@vaswani2017]. Deep models need more data, train for longer and are harder to interpret, which matters when a utility must justify its decisions.

## Smart Metering and Anomaly Detection

Smart-meter analytics raises problems of data volume, privacy and security [@wang2019smartmeter], and labelled records of leaks or faults are rare, so anomaly detection is mostly unsupervised. Isolation Forest isolates unusual points with random splits instead of modelling normal behaviour, and runs in linear time [@liu2008]; a simpler method, used in this study, flags large residuals of a forecasting model. The BattLeDIM competition supplied labelled leaks on a simulated network and concluded that leak-detection methods still need further development [@vrachimis2022battledim].

## Summary of Literature

{{tab:tab_literature}} summarises the reviewed studies with the method, data, main finding and main limitation of each.

[[TAB:tab_literature]]

## Research Gap

The reviewed studies treat water demand and electrical load separately and seldom carry forecasts into operation. None of them compares statistical, machine-learning and deep-learning models on the same chronological splits for both resources, or links the forecasts to anomaly detection on labelled events, to an optimisation that uses them and to dashboards. This study addresses that gap with one pipeline for both resources.
