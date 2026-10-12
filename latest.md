# Snapshot Quant OS — 2026-10-12 18:51 UTC

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

- baja_vol: actualizado hace 97.6 min
- btc_tendencia: actualizado hace 97.6 min
- carry_funding: actualizado hace 97.6 min
- combinada: actualizado hace 97.6 min
- examen_2x: actualizado hace 97.6 min
- flujo_7d: actualizado hace 97.6 min
- flujo_reg200: actualizado hace 97.6 min
- flujo_sectorial: actualizado hace 97.6 min
- flujo_v1: actualizado hace 97.6 min
- lider_azar: actualizado hace 97.6 min
- lider_corto: actualizado hace 97.6 min
- lider_sin_x: actualizado hace 97.6 min
- lider_x: actualizado hace 97.6 min
- mezcla_flujo_carry: actualizado hace 97.6 min
- poly_updown: actualizado hace 7366.8 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 0 | 97.4 |
| binance_perp/depth_snapshots | 0 | 101.0 |
| binance_perp/forced_liquidations | 0 | 97.9 |
| binance_perp/futures_market_metrics | 0 | 97.9 |
| binance_perp/futures_open_interest | 0 | 97.9 |
| binance_perp/futures_positioning | 0 | 98.0 |
| binance_perp/orderbook_l2_depth | 0 | 97.9 |
| binance_perp/trade_ticks | 0 | 97.9 |
| deribit/bbo_ticks | 0 | 97.9 |
| deribit/deribit_metrics | 0 | 97.9 |
| deribit/trade_ticks | 0 | 97.9 |
| dexscreener/token_boosts | 0 | 101.0 |
| dexscreener/token_prices | 0 | 98.0 |
| dexscreener/token_profiles | 0 | 98.0 |
| limitless/limitless_book | 0 | 98.0 |
| limitless/limitless_markets | 0 | 100.0 |
| polymarket/bbo_ticks | 0 | 97.9 |
| polymarket/orderbook_l2_depth | 0 | 97.9 |
| polymarket/polymarket_metadata_history | 0 | 99.9 |
| polymarket/trade_ticks | 0 | 98.9 |
| pumpfun/creator_funding | 0 | 98.0 |
| pumpfun/pumpfun_completes | 0 | 98.0 |
| pumpfun/pumpfun_creates | 0 | 98.0 |
| pumpfun/pumpfun_trades | 0 | 98.0 |
| pumpfun/x_mentions | 0 | 8246.9 |
| telegram/calls | 0 | 103.0 |

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