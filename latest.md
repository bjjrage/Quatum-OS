# Snapshot Quant OS — 2026-10-09 23:51 UTC

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

- baja_vol: actualizado hace 1.0 min
- btc_tendencia: actualizado hace 1.0 min
- carry_funding: actualizado hace 1.0 min
- combinada: actualizado hace 1.0 min
- examen_2x: actualizado hace 1.0 min
- flujo_7d: actualizado hace 1.0 min
- flujo_v1: actualizado hace 1.0 min
- lider_azar: actualizado hace 1.0 min
- lider_corto: actualizado hace 1.0 min
- lider_sin_x: actualizado hace 1.0 min
- lider_x: actualizado hace 1.0 min
- poly_updown: actualizado hace 3346.8 min
- pump_azar: actualizado hace 4226.9 min
- pump_billeteras: actualizado hace 4227.0 min
- pump_billeteras_2x: actualizado hace 4227.0 min
- pump_billeteras_azar: actualizado hace 4227.0 min
- pump_detector_tarde: actualizado hace 4227.0 min
- pump_grupo: actualizado hace 4227.0 min
- pump_grupo_aguantar: actualizado hace 4227.0 min
- pump_grupo_nicho: actualizado hace 4227.0 min
- pump_nicho: actualizado hace 4227.0 min
- pump_nicho_azar: actualizado hace 4227.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 473 | -0.3 |
| binance_perp/depth_snapshots | 16 | 2.8 |
| binance_perp/forced_liquidations | 58 | 0.6 |
| binance_perp/futures_market_metrics | 61 | -0.4 |
| binance_perp/futures_open_interest | 61 | -0.4 |
| binance_perp/orderbook_l2_depth | 120 | -0.4 |
| binance_perp/trade_ticks | 61 | -0.4 |
| deribit/bbo_ticks | 61 | -0.4 |
| deribit/deribit_metrics | 61 | -0.4 |
| deribit/trade_ticks | 36 | 0.6 |
| dexscreener/token_boosts | 7 | 5.0 |
| dexscreener/token_prices | 59 | -0.0 |
| dexscreener/token_profiles | 20 | -0.0 |
| limitless/limitless_book | 60 | -0.0 |
| limitless/limitless_markets | 13 | -0.0 |
| polymarket/bbo_ticks | 662 | -0.8 |
| polymarket/orderbook_l2_depth | 61 | -0.4 |
| polymarket/polymarket_metadata_history | 17 | -0.4 |
| polymarket/trade_ticks | 57 | -0.4 |
| pumpfun/creator_funding | 60 | -0.0 |
| pumpfun/pumpfun_completes | 36 | -0.0 |
| pumpfun/pumpfun_creates | 60 | -0.0 |
| pumpfun/pumpfun_trades | 60 | -0.0 |
| pumpfun/x_mentions | 0 | 4226.9 |
| telegram/calls | 9 | 3.0 |

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
{"timestamp_utc": "2026-10-09T22:54:51Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T22:54:53Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-09T22:55:10Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-09T22:55:12Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-09T22:55:27Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T22:55:48Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T23:20:26Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T23:36:20Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.