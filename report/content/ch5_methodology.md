# Details of the Study: Methodology

## System Architecture

{{fig:fig_architecture}} shows the system in five layers: data sources; a pipeline that downloads, cleans and turns the data into features; three families of forecasting models; analytics that turn forecasts into anomaly alarms and a pumping schedule; and delivery through a REST application programming interface (API), a dashboard and a Power BI dataset.

[[FIG:fig_architecture]]

## Datasets

{{tab:tab_datasets}} lists the sources. Water demand is the inflow of district metered area 3 of the BWDF data [@alvisi2025bwdf], chosen because it had the fewest missing values; the other districts served as a robustness check.

[[TAB:tab_datasets]]

## Data Preprocessing

Minute readings were averaged to hourly values. Gaps of up to {{c:cleaning.max_interpolate_hours}} hours were interpolated; longer gaps ({{e:electricity.long_gap_runs}} for electricity, {{e:water.long_gap_runs}} for water) were left missing and excluded from evaluation, never filled with invented values. Daylight-saving changes were resolved explicitly, and outliers were flagged with a rolling median absolute deviation (MAD) rule but kept as genuine demand. The data were split chronologically: for electricity, training ran to {{m:electricity.d1.split_dates.train.1|date}}, validation to {{m:electricity.d1.split_dates.val.1|date}}, and testing began on {{m:electricity.d1.split_dates.test.0|date}}; for water, the last {{c:splits.water.test_weeks}} weeks formed the test period.

{{fig:fig_eda_profiles}} shows the daily profiles: electricity peaks in the morning and more strongly in the evening, and water demand peaks in the morning, later at weekends. Daily electricity use fell with temperature (correlation {{e:electricity.corr_daily_value_temperature_train|.2f}}), reflecting electric heating, while water demand rose in warm weather ({{e:water.corr_daily_value_temperature_train|.2f}}).

[[FIG:fig_eda_profiles]]

## Feature Engineering

Each forecast is made at midnight for the next {{c:horizons.d1.steps}} hours (D1) or {{c:horizons.w1.steps}} days (W1). Calendar features encode hour, weekday and month as sine and cosine pairs and flag weekends and holidays. Under the lag rule every lag is at least one horizon old: {{c:horizons.d1.lags|list}} hours for D1 and {{c:horizons.w1.lags|list}} days for W1. Weather at the target time completes the inputs, and a perturbation test confirmed that no feature uses data after its origin.

## Forecasting Models

Eight models used identical inputs and splits. The seasonal-naive baseline repeats the value one week earlier; SARIMA [@box2015] used orders chosen by the Akaike information criterion; Ridge regression, Random Forest [@breiman2001] and XGBoost [@chen2016] predict every step from one table; and LSTM [@hochreiter1997], GRU [@cho2014] and CNN-LSTM networks read the past {{c:models.deep.window.d1}} hours or {{c:models.deep.window.w1}} days and output all steps at once. All hyper-parameters, including an option to model demand relative to its recent level, were chosen on validation data.

## Evaluation Protocol and Metrics

Each model made one forecast per origin over the validation and test periods without refitting, and all models were scored on the same origins [@hyndman2021] with the mean absolute error (MAE), root mean square error (RMSE) and mean absolute percentage error (MAPE), where y_{t} is the actual value, ŷ_{t} the forecast and n the number of points.

[[EQ:eq_mae]]

[[EQ:eq_rmse]]

[[EQ:eq_mape]]

MAPE ignored actual values below {{c:metrics.mape_min_fraction_of_train_mean|.0%}} of the training mean, and skill is the reduction in MAE relative to the seasonal-naive forecast. The model with the lowest validation MAE was selected, and the Diebold-Mariano test [@diebold1995] checked whether its test error differed significantly from the best alternative.

## Anomaly Detection

The first detector computes a robust z-score of the residual r_{t} of the selected next-day model over the previous {{c:anomaly.rolling_window_hours}} hours ({{eq:eq_zscore}}) and raises an alarm when it exceeds k in absolute value for m consecutive hours; the second is an Isolation Forest [@liu2008]. Both were tuned on validation data and scored on BattLeDIM leaks [@vrachimis2022battledim] and on injected electricity anomalies.

[[EQ:eq_zscore]]

## Pump Scheduling Optimisation

For each test day a linear programme chooses the hourly pumped volume p_{h} that minimises the energy cost in {{eq:eq_lp_objective}}, where c_{h} is the tariff and e the energy per cubic metre, subject to the tank balance, level limits, pump capacity and end-of-day level in {{eq:eq_lp_constraints}}, with forecast demand d_{h}.

[[EQ:eq_lp_objective]]

[[EQ:eq_lp_constraints]]

The plan was then run against the actual demand with corrective pumping whenever the tank would fall below its minimum, and compared with demand-following pumping, a level-triggered rule [@antunes2018] and perfect foresight, using illustrative tank, pump and tariff values.

## Implementation

The system uses Python with pandas, statsmodels, scikit-learn, XGBoost, TensorFlow and SciPy, a Flask REST API, a Streamlit dashboard and a Power BI export. One command rebuilds every result from the raw data with a fixed seed, and automated tests check leakage, metrics, the optimiser and the API.
