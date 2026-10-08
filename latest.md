# Snapshot Quant OS — 2026-10-08 16:51 UTC

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

- baja_vol: actualizado hace 0.7 min
- btc_tendencia: actualizado hace 0.7 min
- carry_funding: actualizado hace 0.7 min
- combinada: actualizado hace 0.7 min
- examen_2x: actualizado hace 0.7 min
- flujo_7d: actualizado hace 0.7 min
- flujo_v1: actualizado hace 0.7 min
- lider_azar: actualizado hace 0.7 min
- lider_corto: actualizado hace 0.7 min
- lider_sin_x: actualizado hace 0.7 min
- lider_x: actualizado hace 0.7 min
- poly_updown: actualizado hace 1486.8 min
- pump_azar: actualizado hace 2366.9 min
- pump_billeteras: actualizado hace 2366.9 min
- pump_billeteras_2x: actualizado hace 2366.9 min
- pump_billeteras_azar: actualizado hace 2366.9 min
- pump_detector_tarde: actualizado hace 2366.9 min
- pump_grupo: actualizado hace 2366.9 min
- pump_grupo_aguantar: actualizado hace 2366.9 min
- pump_grupo_nicho: actualizado hace 2366.9 min
- pump_nicho: actualizado hace 2366.9 min
- pump_nicho_azar: actualizado hace 2366.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1375 | -0.4 |
| binance_perp/depth_snapshots | 17 | 3.2 |
| binance_perp/forced_liquidations | 59 | 0.3 |
| binance_perp/futures_market_metrics | 59 | 0.3 |
| binance_perp/futures_open_interest | 60 | 0.4 |
| binance_perp/orderbook_l2_depth | 106 | 0.3 |
| binance_perp/trade_ticks | 199 | -0.1 |
| deribit/bbo_ticks | 73 | 0.3 |
| deribit/deribit_metrics | 103 | 0.3 |
| deribit/trade_ticks | 60 | 0.3 |
| dexscreener/token_boosts | 5 | 4.5 |
| dexscreener/token_prices | 61 | -0.5 |
| dexscreener/token_profiles | 26 | 0.5 |
| limitless/limitless_book | 61 | -0.5 |
| limitless/limitless_markets | 15 | -0.5 |
| polymarket/bbo_ticks | 1107 | -0.7 |
| polymarket/orderbook_l2_depth | 61 | -0.7 |
| polymarket/polymarket_metadata_history | 16 | -0.7 |
| polymarket/trade_ticks | 58 | -0.7 |
| pumpfun/creator_funding | 61 | -0.5 |
| pumpfun/pumpfun_completes | 36 | 2.5 |
| pumpfun/pumpfun_creates | 61 | -0.5 |
| pumpfun/pumpfun_trades | 61 | -0.5 |
| pumpfun/x_mentions | 0 | 2366.9 |
| telegram/calls | 6 | 4.5 |

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
{"timestamp_utc": "2026-10-08T16:50:43Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T16:50:50Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T16:50:57Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T16:51:02Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T16:51:13Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T16:51:31Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T16:51:36Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T16:51:43Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.