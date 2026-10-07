# X (sentimiento) vs on-chain en pump.fun

Consultas de X: 44 mints con entrada y salida dentro de los datos. Costo por lado 1.25%, latencia 2.0s. Gasto total registrado en X: US$ 3.61.

- `x_status`: [('BUDGET_EXHAUSTED', 4898), (None, 53), ('X_NEGATIVE', 1)]
- `consumer`: [('pump_x_watcher', 4899), (None, 53)]
- Cortes on-chain (unique_buyers_5m, calibrados en H1): 63 / 89. Alcance alto = max_followers ≥ 0.

## H1

| grupo | n | neto 5m medio/mediano % | neto 15m medio/mediano % | neto 60m medio/mediano % | toca 2x antes de -50% | toca -50% antes de 2x | máx. múltiplo mediano 2h | stale 15m |
|---|---|---|---|---|---|---|---|---|
| todos | 22 | 0.7 / -3.9 | -14.5 / -43.1 | 11.2 / -55.3 | 23% | 55% | 1.38x | 32% |

## H2

| grupo | n | neto 5m medio/mediano % | neto 15m medio/mediano % | neto 60m medio/mediano % | toca 2x antes de -50% | toca -50% antes de 2x | máx. múltiplo mediano 2h | stale 15m |
|---|---|---|---|---|---|---|---|---|
| todos | 22 | -7.5 / -6.6 | -8.5 / -3.7 | -7.1 / -5.0 | 0% | 27% | 1.03x | 91% |

## todo

| grupo | n | neto 5m medio/mediano % | neto 15m medio/mediano % | neto 60m medio/mediano % | toca 2x antes de -50% | toca -50% antes de 2x | máx. múltiplo mediano 2h | stale 15m |
|---|---|---|---|---|---|---|---|---|
| todos | 44 | -3.4 / -5.9 | -11.5 / -23.2 | 2.1 / -20.3 | 11% | 41% | 1.24x | 61% |
| on-chain bajo | 21 | 1.1 / -4.5 | -5.5 / -2.5 | -10.5 / -6.3 | 14% | 29% | 1.03x | 67% |
|   on-chain bajo · sin posts | 16 | 11.5 / -3.5 | 0.7 / -2.5 | 3.2 / -5.0 | 12% | 19% | 1.00x | 75% |
|   on-chain bajo · alcance alto | 21 | 1.1 / -4.5 | -5.5 / -2.5 | -10.5 / -6.3 | 14% | 29% | 1.03x | 67% |

## Cómo leerlo

- X sirve solo si, dentro del MISMO nivel on-chain, `con posts` / `alcance alto` gana a su contraparte en H1 **y** en H2.
- Si solo gana en una mitad, es ruido. Si gana `sin posts`, X llega tarde (el pump ya pasó).
- `toca 2x antes de -50%` es la regla de la escalera de pump_paper: es la métrica más cercana a cómo operás.