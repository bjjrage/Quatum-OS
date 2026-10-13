# Snapshot Quant OS — 2026-10-13 09:51 UTC

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

- baja_vol: actualizado hace 0.4 min
- btc_tendencia: actualizado hace 0.4 min
- carry_funding: actualizado hace 0.4 min
- combinada: actualizado hace 0.4 min
- examen_2x: actualizado hace 0.4 min
- flujo_7d: actualizado hace 0.4 min
- flujo_reg200: actualizado hace 0.4 min
- flujo_sectorial: actualizado hace 0.4 min
- flujo_v1: actualizado hace 0.4 min
- lider_azar: actualizado hace 0.4 min
- lider_corto: actualizado hace 0.4 min
- lider_sin_x: actualizado hace 0.4 min
- lider_x: actualizado hace 0.4 min
- mezcla_flujo_carry: actualizado hace 0.4 min
- poly_updown: actualizado hace 8266.8 min
- unlock_short_v1: actualizado hace 45.8 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1341 | -1.0 |
| binance_perp/depth_snapshots | 20 | -0.5 |
| binance_perp/forced_liquidations | 60 | -0.6 |
| binance_perp/futures_market_metrics | 61 | -0.6 |
| binance_perp/futures_open_interest | 61 | -0.6 |
| binance_perp/futures_positioning | 61 | -0.5 |
| binance_perp/orderbook_l2_depth | 153 | -1.6 |
| binance_perp/trade_ticks | 75 | -1.6 |
| deribit/bbo_ticks | 11 | 49.6 |
| deribit/deribit_metrics | 23 | -1.6 |
| deribit/trade_ticks | 21 | -1.6 |
| dexscreener/token_boosts | 2 | -1.3 |
| dexscreener/token_prices | 60 | -1.3 |
| dexscreener/token_profiles | 12 | 7.7 |
| limitless/limitless_book | 62 | -1.3 |
| limitless/limitless_markets | 13 | 0.7 |
| polymarket/bbo_ticks | 926 | -2.5 |
| polymarket/orderbook_l2_depth | 63 | -2.6 |
| polymarket/polymarket_metadata_history | 12 | -0.6 |
| polymarket/trade_ticks | 61 | -2.6 |
| pumpfun/creator_funding | 62 | -2.3 |
| pumpfun/pumpfun_completes | 25 | 0.7 |
| pumpfun/pumpfun_creates | 63 | -2.3 |
| pumpfun/pumpfun_trades | 63 | -2.3 |
| pumpfun/x_mentions | 0 | 9146.9 |
| telegram/calls | 8 | -2.3 |

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
{"timestamp_utc": "2026-10-13T09:37:33Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: server rejected WebSocket connection: HTTP 503. Reconnecting in 30.0s..."}
{"timestamp_utc": "2026-10-13T09:38:04Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: server rejected WebSocket connection: HTTP 503. Reconnecting in 30.0s..."}
{"timestamp_utc": "2026-10-13T09:38:34Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: server rejected WebSocket connection: HTTP 503. Reconnecting in 30.0s..."}
{"timestamp_utc": "2026-10-13T09:39:05Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: server rejected WebSocket connection: HTTP 503. Reconnecting in 30.0s..."}
{"timestamp_utc": "2026-10-13T09:39:36Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: server rejected WebSocket connection: HTTP 503. Reconnecting in 30.0s..."}
{"timestamp_utc": "2026-10-13T09:40:06Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: server rejected WebSocket connection: HTTP 503. Reconnecting in 30.0s..."}
{"timestamp_utc": "2026-10-13T09:40:37Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: server rejected WebSocket connection: HTTP 503. Reconnecting in 30.0s..."}
{"timestamp_utc": "2026-10-13T09:45:28Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.