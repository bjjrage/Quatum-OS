# Snapshot Quant OS — 2026-10-13 16:51 UTC

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

- baja_vol: actualizado hace 1.5 min
- btc_tendencia: actualizado hace 1.5 min
- carry_funding: actualizado hace 1.5 min
- combinada: actualizado hace 1.5 min
- examen_2x: actualizado hace 1.5 min
- flujo_7d: actualizado hace 1.5 min
- flujo_reg200: actualizado hace 1.5 min
- flujo_sectorial: actualizado hace 1.5 min
- flujo_v1: actualizado hace 1.5 min
- lider_azar: actualizado hace 1.5 min
- lider_corto: actualizado hace 1.5 min
- lider_sin_x: actualizado hace 1.5 min
- lider_x: actualizado hace 1.5 min
- mezcla_flujo_carry: actualizado hace 1.5 min
- poly_updown: actualizado hace 8686.8 min
- unlock_short_v1: actualizado hace 45.6 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1337 | -1.2 |
| binance_perp/depth_snapshots | 19 | 0.2 |
| binance_perp/forced_liquidations | 59 | -1.4 |
| binance_perp/futures_market_metrics | 60 | -1.4 |
| binance_perp/futures_open_interest | 61 | -1.4 |
| binance_perp/futures_positioning | 61 | -0.8 |
| binance_perp/orderbook_l2_depth | 162 | -1.4 |
| binance_perp/trade_ticks | 70 | -1.4 |
| deribit/bbo_ticks | 61 | -1.4 |
| deribit/deribit_metrics | 61 | -1.4 |
| deribit/trade_ticks | 54 | -0.4 |
| dexscreener/token_boosts | 6 | 6.7 |
| dexscreener/token_prices | 61 | -1.4 |
| dexscreener/token_profiles | 25 | -1.4 |
| limitless/limitless_book | 62 | -1.4 |
| limitless/limitless_markets | 14 | 0.6 |
| polymarket/bbo_ticks | 810 | -2.4 |
| polymarket/orderbook_l2_depth | 62 | -2.4 |
| polymarket/polymarket_metadata_history | 16 | -0.4 |
| polymarket/trade_ticks | 56 | -2.4 |
| pumpfun/creator_funding | 63 | -2.4 |
| pumpfun/pumpfun_completes | 43 | -2.4 |
| pumpfun/pumpfun_creates | 63 | -2.4 |
| pumpfun/pumpfun_trades | 68 | -2.4 |
| pumpfun/x_mentions | 0 | 9566.9 |
| telegram/calls | 15 | -2.4 |

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
{"timestamp_utc": "2026-10-13T15:55:00Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 3.4s..."}
{"timestamp_utc": "2026-10-13T15:55:21Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T16:04:16Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T16:20:47Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T16:36:57Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T16:37:04Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T16:50:07Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T16:54:03Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.