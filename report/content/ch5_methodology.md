# Details of the Study: Methodology

## System Architecture

{{fig:fig_architecture}} shows the system in five layers. The data sources supply interval consumption, weather and leak labels. The data pipeline downloads each source with a checksum, cleans it and builds a feature store. Three families of forecasting models read the same features. The analytics layer turns forecasts into anomaly alarms and a pumping schedule, and the delivery layer serves the results through a REST application programming interface (API), an interactive dashboard and a Power BI dataset.

[[FIG:fig_architecture]]

## Datasets

{{tab:tab_datasets}} lists the four sources. Electricity is the active power of one household near Paris [@uci2012household], with weather from the Open-Meteo archive [@openmeteo]. Water demand is the inflow of district metered area 3 of the BWDF dataset [@alvisi2025bwdf], chosen because it had the fewest missing values; the other districts were used for a robustness check. Leak labels come from the BattLeDIM benchmark [@vrachimis2022battledim].

[[TAB:tab_datasets]]

## Data Preprocessing

Minute readings were averaged to hourly values, and an hour was kept only when most of its minutes were present. Gaps of up to {{c:cleaning.max_interpolate_hours}} hours were interpolated; longer gaps were left missing and excluded from evaluation, never filled with invented values. The electricity series had {{e:electricity.long_gap_runs}} such long gaps and the water series {{e:water.long_gap_runs}}. The household meter's clock does not follow daylight saving, whereas the water data use local time, so the repeated autumn hour was averaged and the missing spring hour interpolated. Outliers were flagged with a rolling median and median absolute deviation (MAD) rule but kept, because peaks are genuine demand. The data were split chronologically: for electricity, training ran to {{m:electricity.d1.split_dates.train.1|date}}, validation to {{m:electricity.d1.split_dates.val.1|date}}, and the test period started on {{m:electricity.d1.split_dates.test.0|date}}; for water, the last {{c:splits.water.test_weeks}} weeks formed the test period.

{{fig:fig_eda_profiles}} shows the average daily profiles. Household electricity has a sharp weekday morning peak and a larger evening peak, with higher daytime use at weekends; water demand peaks in the morning, later at weekends, and again in the evening. Daily electricity use fell as temperature rose (correlation {{e:electricity.corr_daily_value_temperature_train|.2f}} in training), reflecting electric heating, while water demand rose in warm weather ({{e:water.corr_daily_value_temperature_train|.2f}}).

[[FIG:fig_eda_profiles]]

## Feature Engineering

Each forecast is made at midnight, the forecast origin, for the next {{c:horizons.d1.steps}} hours (D1) or the next {{c:horizons.w1.steps}} days (W1). Calendar features encode the hour, day of week and month as sine and cosine pairs and flag weekends, public holidays and the days around them. Lag features use past demand, and a lag rule prevents look-ahead leakage: every lag is at least one horizon old, so D1 uses lags of {{c:horizons.d1.lags|list}} hours and W1 lags of {{c:horizons.w1.lags|list}} days, together with recent averages computed at the origin. Weather at the target time (temperature, humidity and precipitation, with heating and cooling degree hours) completes the inputs. A perturbation test confirmed the rule: changing every value after an origin left all features of that origin unchanged.

## Forecasting Models

Eight models were compared on identical inputs and splits. The seasonal-naive baseline repeats the value of the same hour or weekday one week earlier. SARIMA [@box2015] used orders chosen by the Akaike information criterion and was updated with new observations without re-estimating its parameters. Ridge regression, Random Forest [@breiman2001] and XGBoost [@chen2016] predict every step of the horizon from one table in which the step index is a feature. LSTM [@hochreiter1997], GRU [@cho2014] and CNN-LSTM networks read a window of the past {{c:models.deep.window.d1}} hours or {{c:models.deep.window.w1}} days together with the calendar, weather and lag features of the target steps, and output all steps at once. Because the water demand fell to a new level in late 2022, the tabular and deep models could also work relative to the recent level, an option chosen on validation data. All hyper-parameters were selected on the validation period only.

## Evaluation Protocol and Metrics

Every model produced one forecast per origin over the validation and test periods (a rolling-origin evaluation) without refitting inside a period, and all models were scored on the same origins [@hyndman2021]. Accuracy was measured by the mean absolute error (MAE), the root mean square error (RMSE) and the mean absolute percentage error (MAPE), where y_{t} is the actual value, ŷ_{t} the forecast and n the number of points.

[[EQ:eq_mae]]

[[EQ:eq_rmse]]

[[EQ:eq_mape]]

MAPE excluded actual values below {{c:metrics.mape_min_fraction_of_train_mean|.0%}} of the training mean, where percentage errors explode. Skill is the reduction in MAE relative to the seasonal-naive forecast. The operational model for each task was the one with the lowest validation MAE, and the Diebold-Mariano test [@diebold1995] checked whether its test error differed significantly from that of the best alternative.

## Anomaly Detection

The first detector uses the residual r_{t} of the selected next-day model. A robust z-score compares each residual with the median and MAD of the residuals of the previous {{c:anomaly.rolling_window_hours}} hours, as in {{eq:eq_zscore}}.

[[EQ:eq_zscore]]

An alarm is raised when the absolute z-score exceeds a threshold k for m consecutive hours, and nearby alarms are merged into one event. The second detector is an Isolation Forest [@liu2008] on the residual, the hour, the weekday and recent consumption statistics. Both were tuned on the validation period. The water detectors were evaluated on BattLeDIM network inflow against the real leak list [@vrachimis2022battledim]. The electricity detectors were evaluated on a copy of the test period into which spikes, level shifts and slow drifts were injected; these labels are reported as injected throughout.

## Pump Scheduling Optimisation

For each test day a linear programme chooses the hourly pumped volume p_{h} that minimises the energy cost in {{eq:eq_lp_objective}}, where c_{h} is the tariff of hour h and e the energy per cubic metre, subject to the tank balance, level limits, pump capacity and end-of-day level in {{eq:eq_lp_constraints}}, with d_{h} the forecast demand.

[[EQ:eq_lp_objective]]

[[EQ:eq_lp_constraints]]

The plan made from the forecast was then run against the actual demand: whenever the tank would fall below its minimum, corrective pumping at that hour's tariff was added, so forecast errors carry a cost. Plans from the selected forecast, the seasonal-naive forecast and the actual demand (perfect foresight) were compared with demand-following pumping and a level-triggered on/off rule, the practice described by Antunes et al. [@antunes2018]. The tank, pump and tariff values are illustrative, with off-peak, normal and peak tariff bands expressed as multipliers of a base rate.

## Implementation

The system was written in Python. Pandas handled the data, statsmodels the SARIMA models, scikit-learn and XGBoost the tabular models, TensorFlow the deep networks and SciPy the linear programme. A Flask REST API serves metrics, forecasts, anomalies and schedules; a Streamlit dashboard presents them; and a star-schema export feeds Power BI. A single command rebuilds every result from the raw data with a fixed random seed, and automated tests check leakage, metrics, the optimiser, the API and the dashboard.
