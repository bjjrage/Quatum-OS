# Snapshot Quant OS — 2026-10-12 17:51 UTC

## Polymarket up/down (paper)

- Señales 425 · llenadas 291 · perdidas 134 (32% se las llevó otro)
- PnL Binance US$ 1817.40 · PnL oficial US$ -84.10 (291 resueltas) · aciertos 40% · t por ventana -0.8387298218090913
- Criterio: todavía no

## Salud

- api: NEVER_STARTED
- web: NEVER_STARTED
- os_launcher: NEVER_STARTED
- supervisor: NEVER_STARTED
- markets_recorder: STOPPED
- paper_runtime: STOPPED
- pumpfun_recorder: NEVER_STARTED
- pumpfun_paper: DISABLED
- leader_paper: STOPPED
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 37.7 min
- btc_tendencia: actualizado hace 37.7 min
- carry_funding: actualizado hace 37.7 min
- combinada: actualizado hace 37.7 min
- examen_2x: actualizado hace 37.7 min
- flujo_7d: actualizado hace 37.7 min
- flujo_reg200: actualizado hace 37.7 min
- flujo_sectorial: actualizado hace 37.7 min
- flujo_v1: actualizado hace 37.7 min
- lider_azar: actualizado hace 37.7 min
- lider_corto: actualizado hace 37.7 min
- lider_sin_x: actualizado hace 37.7 min
- lider_x: actualizado hace 37.7 min
- mezcla_flujo_carry: actualizado hace 37.7 min
- poly_updown: actualizado hace 7306.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 480 | 37.5 |
| binance_perp/depth_snapshots | 7 | 41.1 |
| binance_perp/forced_liquidations | 22 | 37.9 |
| binance_perp/futures_market_metrics | 22 | 37.9 |
| binance_perp/futures_open_interest | 22 | 37.9 |
| binance_perp/futures_positioning | 20 | 38.1 |
| binance_perp/orderbook_l2_depth | 50 | 37.9 |
| binance_perp/trade_ticks | 37 | 37.9 |
| deribit/bbo_ticks | 22 | 37.9 |
| deribit/deribit_metrics | 22 | 37.9 |
| deribit/trade_ticks | 21 | 37.9 |
| dexscreener/token_boosts | 2 | 41.0 |
| dexscreener/token_prices | 22 | 38.0 |
| dexscreener/token_profiles | 14 | 38.0 |
| limitless/limitless_book | 22 | 38.0 |
| limitless/limitless_markets | 5 | 40.0 |
| polymarket/bbo_ticks | 246 | 37.9 |
| polymarket/orderbook_l2_depth | 22 | 37.9 |
| polymarket/polymarket_metadata_history | 6 | 39.9 |
| polymarket/trade_ticks | 21 | 38.9 |
| pumpfun/creator_funding | 22 | 38.0 |
| pumpfun/pumpfun_completes | 13 | 38.0 |
| pumpfun/pumpfun_creates | 22 | 38.0 |
| pumpfun/pumpfun_trades | 22 | 38.0 |
| pumpfun/x_mentions | 0 | 8187.0 |
| telegram/calls | 5 | 43.0 |

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
{"timestamp_utc": "2026-10-12T17:01:37Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:02:09Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:02:13Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:02:24Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:03:27Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:03:42Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:04:16Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:07:42Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.