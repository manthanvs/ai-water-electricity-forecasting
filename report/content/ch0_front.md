<!-- Front matter. Manthan must rewrite the Abstract and the Acknowledgement in his own words (STUDENT_REVIEW.md). -->

# Abstract

Water utilities and electricity distribution companies still plan much of their supply from historical averages and manual judgement, although smart meters now record consumption at hourly or finer intervals. This seminar examines how artificial intelligence applied to such interval data can support the short-term planning of both resources. A reproducible pipeline was built on public data: minute-level electricity readings of one household in France, hourly inflows of district metered areas in north-east Italy, and a benchmark water network with labelled leaks. Seasonal-naive, SARIMA, Ridge regression, Random Forest, XGBoost, LSTM, GRU and CNN-LSTM models were compared on identical chronological splits for next-day hourly and next-week daily forecasts, with weather, calendar and holiday predictors. On the held-out test period, the selected next-day models reduced the mean absolute error of the seasonal-naive baseline by {{m:electricity.d1.test.SEL.skill|.0%}} for electricity and by {{m:water.d1.test.SEL.skill|.0%}} for water, whereas the selected weekly water model was not significantly better than the baseline. A residual-based detector found {{a:water.residual_zscore.test.n_detected}} of the {{a:water.residual_zscore.test.n_labels}} leaks that began in the test period, and a linear programme that schedules pumping from the water forecast lowered an illustrative energy cost by {{o:water_pump.summary.selected_forecast.saving_pct_vs_demand_following|.0f}} percent against demand-following operation. The results are delivered through a Flask API, a Streamlit dashboard and a Power BI dataset. Deep learning gave the most accurate next-day forecasts for the volatile household load, while gradient-boosted trees were best for the smoother district demand.

Keywords: water demand forecasting; electricity load forecasting; smart meters; deep learning; anomaly detection; pump scheduling

# Acknowledgement

I express my sincere gratitude to my Seminar Guide, Prof. Dr. Anjana Arakerimath, Head of the Department of Master of Computer Application, for her guidance, constructive feedback and encouragement throughout this seminar. Her suggestions shaped both the direction of the study and the presentation of this report.

I am grateful to Dr. Govind N. Kulkarni, Director, Pimpri Chinchwad College of Engineering, Pune, for the facilities and the academic environment that made this work possible. I also thank the faculty members and staff of the Department of Master of Computer Application for their support and timely help.

I acknowledge the organisations that make their data openly available: the UCI Machine Learning Repository, the organisers of the Battle of the Water Demand Forecasting and of the BattLeDIM competition, and Open-Meteo.

Finally, I thank my family and friends for their constant encouragement.

Mr. Manthan Sankpal

# Nomenclature

## Abbreviations

- ANN: Artificial neural network
- API: Application programming interface
- ARIMA: Autoregressive integrated moving average
- BWDF: Battle of the Water Demand Forecasting
- CNN: Convolutional neural network
- D1: Next-day forecast of 24 hourly values
- DMA: District metered area
- GRU: Gated recurrent unit
- k-NN: k-nearest neighbours
- LSTM: Long short-term memory
- MAD: Median absolute deviation
- MAE: Mean absolute error
- MAPE: Mean absolute percentage error
- RDSS: Revamped Distribution Sector Scheme
- REST: Representational state transfer
- RMSE: Root mean square error
- SARIMA: Seasonal autoregressive integrated moving average
- SVM: Support vector machine
- W1: Next-week forecast of 7 daily totals
- XGBoost: Extreme gradient boosting

## Symbols

- y_{t}: Actual value at time t
- ŷ_{t}: Forecast of y_{t}
- n: Number of evaluated points
- r_{t}: Forecast residual, y_{t} − ŷ_{t}
- z_{t}: Robust z-score of the residual
- k, m: Alarm threshold and number of consecutive hours
- h: Hour of the day in the pumping plan
- p_{h}: Volume pumped in hour h
- d_{h}: Forecast water demand in hour h
- L_{h}: Tank level at the end of hour h
- L_{min}, L_{max}: Lower and upper tank level limits
- P_{max}: Pump capacity per hour
- c_{h}: Energy tariff in hour h
- e: Energy used per cubic metre pumped
