# Snapshot Quant OS — 2026-10-09 14:51 UTC

## Polymarket up/down (paper)

- Señales 425 · llenadas 291 · perdidas 134 (32% se las llevó otro)
- PnL Binance US$ 1817.40 · PnL oficial US$ -84.10 (291 resueltas) · aciertos 40% · t por ventana -0.8387298218090913
- Criterio: todavía no

## Salud

- api: RUNNING
- web: RUNNING
- os_launcher: RUNNING
- supervisor: RUNNING
- markets_recorder: RUNNING
- paper_runtime: RUNNING
- pumpfun_recorder: RUNNING
- pumpfun_paper: DISABLED
- leader_paper: RUNNING
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 1.1 min
- btc_tendencia: actualizado hace 1.1 min
- carry_funding: actualizado hace 1.1 min
- combinada: actualizado hace 1.1 min
- examen_2x: actualizado hace 1.1 min
- flujo_7d: actualizado hace 1.1 min
- flujo_v1: actualizado hace 1.1 min
- lider_azar: actualizado hace 1.1 min
- lider_corto: actualizado hace 1.1 min
- lider_sin_x: actualizado hace 1.1 min
- lider_x: actualizado hace 1.1 min
- poly_updown: actualizado hace 2806.8 min
- pump_azar: actualizado hace 3686.9 min
- pump_billeteras: actualizado hace 3687.0 min
- pump_billeteras_2x: actualizado hace 3687.0 min
- pump_billeteras_azar: actualizado hace 3687.0 min
- pump_detector_tarde: actualizado hace 3686.9 min
- pump_grupo: actualizado hace 3686.9 min
- pump_grupo_aguantar: actualizado hace 3686.9 min
- pump_grupo_nicho: actualizado hace 3686.9 min
- pump_nicho: actualizado hace 3687.0 min
- pump_nicho_azar: actualizado hace 3687.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1557 | -0.2 |
| binance_perp/depth_snapshots | 19 | -0.1 |
| binance_perp/forced_liquidations | 60 | 0.2 |
| binance_perp/futures_market_metrics | 60 | 0.2 |
| binance_perp/futures_open_interest | 60 | 0.2 |
| binance_perp/orderbook_l2_depth | 148 | 0.2 |
| binance_perp/trade_ticks | 94 | 0.2 |
| deribit/bbo_ticks | 60 | 0.2 |
| deribit/deribit_metrics | 60 | 0.2 |
| deribit/trade_ticks | 60 | 0.2 |
| dexscreener/token_boosts | 6 | 6.4 |
| dexscreener/token_prices | 56 | 0.4 |
| dexscreener/token_profiles | 23 | 0.4 |
| limitless/limitless_book | 60 | 0.4 |
| limitless/limitless_markets | 13 | 0.4 |
| polymarket/bbo_ticks | 464 | -0.1 |
| polymarket/orderbook_l2_depth | 60 | 0.2 |
| polymarket/polymarket_metadata_history | 16 | 0.2 |
| polymarket/trade_ticks | 49 | 0.2 |
| pumpfun/creator_funding | 60 | 0.4 |
| pumpfun/pumpfun_completes | 36 | 4.4 |
| pumpfun/pumpfun_creates | 60 | 0.4 |
| pumpfun/pumpfun_trades | 67 | 0.4 |
| pumpfun/x_mentions | 0 | 3686.9 |
| telegram/calls | 11 | 6.4 |

## Problemas en logs (últimos)

### os_launcher.log
```
Traceback (most recent call last):
```
### poly_paper.log
```
{"timestamp_utc": "2026-10-07T16:01:47Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:01:51Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Binance WS: ConnectionClosedError: no close frame received or sent; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:01:52Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:02:18Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:02:33Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:02:46Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: TimeoutError: timed out during opening handshake; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:02:58Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T16:03:57Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
```
### recorder.log
```
{"timestamp_utc": "2026-10-09T14:31:17Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T14:31:24Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T14:31:30Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T14:32:16Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T14:32:21Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T14:35:09Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T14:40:17Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T14:50:38Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.