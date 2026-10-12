# Summary of findings

Generated from results/metrics.json (2026-10-12T18:54:13+00:00). Test-period numbers; every model is scored on the same forecast origins.

## Electricity, next-day hourly (D1)

- Selected model (lowest validation MAE): GRU. Test MAE 0.397 kW, RMSE 0.565 kW, MAPE 57.2 percent, sMAPE 45.2 percent, R2 0.379, skill versus seasonal naive 0.284.
- Seasonal naive: test MAE 0.555 kW. 7 of 7 models beat it on test.
- Lowest test MAE overall: GRU (0.397 kW); the selected model.
- Best tabular model XGBoost (0.410) versus best deep model GRU (0.397): the deep model is better.
- Diebold-Mariano test, GRU versus LSTM (per-origin MAE): p = 0.021 - the difference is statistically significant at the 5 percent level.
- Without weather inputs, XGBoost test MAE is 0.409 kW (with weather 0.410; change -0.0 percent).
- Without weather inputs, GRU test MAE is 0.397 kW (with weather 0.397; change -0.1 percent).

## Electricity, next-week daily (W1)

- Selected model (lowest validation MAE): XGBoost. Test MAE 4.844 kWh/day, RMSE 6.247 kWh/day, MAPE 29.7 percent, sMAPE 24.0 percent, R2 0.449, skill versus seasonal naive 0.208.
- Seasonal naive: test MAE 6.114 kWh/day. 7 of 7 models beat it on test.
- Lowest test MAE overall: LSTM (4.153 kWh/day); the selected model ranks 5 of 8 on test.
- Best tabular model Random Forest (4.418) versus best deep model LSTM (4.153): the deep model is better.
- Diebold-Mariano test, XGBoost versus LSTM (per-origin MAE): p = 0.244 - the difference is not statistically significant at the 5 percent level.
- Without weather inputs, XGBoost test MAE is 4.756 kWh/day (with weather 4.844; change -1.8 percent).
- Without weather inputs, GRU test MAE is 4.413 kWh/day (with weather 4.470; change -1.3 percent).

## Water, next-day hourly (D1)

- Selected model (lowest validation MAE): XGBoost. Test MAE 0.145 L/s, RMSE 0.196 L/s, MAPE 4.8 percent, sMAPE 4.8 percent, R2 0.946, skill versus seasonal naive 0.224.
- Seasonal naive: test MAE 0.187 L/s. 6 of 7 models beat it on test; not beating it: SARIMA.
- Lowest test MAE overall: XGBoost (0.145 L/s); the selected model.
- Best tabular model XGBoost (0.145) versus best deep model GRU (0.176): the deep model does not beat the tabular model.
- Diebold-Mariano test, XGBoost versus Random Forest (per-origin MAE): p = 0.000 - the difference is statistically significant at the 5 percent level.
- Without weather inputs, XGBoost test MAE is 0.146 L/s (with weather 0.145; change +1.0 percent).
- Without weather inputs, CNN-LSTM test MAE is 0.182 L/s (with weather 0.182; change +0.4 percent).

## Water, next-week daily (W1)

- Selected model (lowest validation MAE): XGBoost. Test MAE 7.213 m3/day, RMSE 9.325 m3/day, MAPE 2.8 percent, sMAPE 2.8 percent, R2 0.389, skill versus seasonal naive 0.026.
- Seasonal naive: test MAE 7.404 m3/day. 5 of 7 models beat it on test; not beating it: SARIMA, Ridge regression.
- Lowest test MAE overall: LSTM (6.677 m3/day); the selected model ranks 5 of 8 on test.
- Best tabular model Random Forest (6.841) versus best deep model LSTM (6.677): the deep model is better.
- Diebold-Mariano test, XGBoost versus LSTM (per-origin MAE): p = 0.576 - the difference is not statistically significant at the 5 percent level.
- Without weather inputs, XGBoost test MAE is 6.721 m3/day (with weather 7.213; change -6.8 percent).
- Without weather inputs, CNN-LSTM test MAE is 7.107 m3/day (with weather 6.821; change +4.2 percent).

## Robustness across water areas

- XGBoost with the DMA 3 hyper-parameters beats seasonal naive on 10 of 10 DMAs (D1, test period); median skill 0.266.
