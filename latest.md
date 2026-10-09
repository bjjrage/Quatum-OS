# Snapshot Quant OS — 2026-10-09 19:51 UTC

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

- baja_vol: actualizado hace 0.6 min
- btc_tendencia: actualizado hace 0.6 min
- carry_funding: actualizado hace 0.6 min
- combinada: actualizado hace 0.6 min
- examen_2x: actualizado hace 0.6 min
- flujo_7d: actualizado hace 0.6 min
- flujo_v1: actualizado hace 0.6 min
- lider_azar: actualizado hace 0.6 min
- lider_corto: actualizado hace 0.6 min
- lider_sin_x: actualizado hace 0.6 min
- lider_x: actualizado hace 0.6 min
- poly_updown: actualizado hace 3106.8 min
- pump_azar: actualizado hace 3986.9 min
- pump_billeteras: actualizado hace 3987.0 min
- pump_billeteras_2x: actualizado hace 3987.0 min
- pump_billeteras_azar: actualizado hace 3987.0 min
- pump_detector_tarde: actualizado hace 3986.9 min
- pump_grupo: actualizado hace 3986.9 min
- pump_grupo_aguantar: actualizado hace 3986.9 min
- pump_grupo_nicho: actualizado hace 3986.9 min
- pump_nicho: actualizado hace 3986.9 min
- pump_nicho_azar: actualizado hace 3986.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 842 | -0.2 |
| binance_perp/depth_snapshots | 20 | 3.8 |
| binance_perp/forced_liquidations | 58 | 0.7 |
| binance_perp/futures_market_metrics | 58 | 0.7 |
| binance_perp/futures_open_interest | 60 | -0.3 |
| binance_perp/orderbook_l2_depth | 123 | -0.3 |
| binance_perp/trade_ticks | 60 | -0.3 |
| deribit/bbo_ticks | 60 | -0.3 |
| deribit/deribit_metrics | 60 | -0.3 |
| deribit/trade_ticks | 58 | -0.3 |
| dexscreener/token_boosts | 6 | -0.4 |
| dexscreener/token_prices | 61 | -0.4 |
| dexscreener/token_profiles | 30 | -0.4 |
| limitless/limitless_book | 61 | -0.4 |
| limitless/limitless_markets | 13 | -0.4 |
| polymarket/bbo_ticks | 770 | -0.6 |
| polymarket/orderbook_l2_depth | 60 | -0.3 |
| polymarket/polymarket_metadata_history | 16 | -0.3 |
| polymarket/trade_ticks | 55 | -0.3 |
| pumpfun/creator_funding | 61 | -0.4 |
| pumpfun/pumpfun_completes | 44 | 2.6 |
| pumpfun/pumpfun_creates | 61 | -0.4 |
| pumpfun/pumpfun_trades | 80 | -0.4 |
| pumpfun/x_mentions | 0 | 3986.9 |
| telegram/calls | 15 | 7.7 |

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
{"timestamp_utc": "2026-10-09T18:54:52Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-09T18:55:07Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
{"timestamp_utc": "2026-10-09T18:55:09Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-09T18:55:18Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T19:08:10Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T19:20:58Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T19:22:07Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T19:35:11Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.