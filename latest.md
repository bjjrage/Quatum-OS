# Snapshot Quant OS — 2026-10-13 13:51 UTC

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

- baja_vol: actualizado hace 0.2 min
- btc_tendencia: actualizado hace 0.2 min
- carry_funding: actualizado hace 0.2 min
- combinada: actualizado hace 0.2 min
- examen_2x: actualizado hace 0.2 min
- flujo_7d: actualizado hace 0.2 min
- flujo_reg200: actualizado hace 0.2 min
- flujo_sectorial: actualizado hace 0.2 min
- flujo_v1: actualizado hace 0.2 min
- lider_azar: actualizado hace 0.2 min
- lider_corto: actualizado hace 0.2 min
- lider_sin_x: actualizado hace 0.2 min
- lider_x: actualizado hace 0.2 min
- mezcla_flujo_carry: actualizado hace 0.2 min
- poly_updown: actualizado hace 8506.8 min
- unlock_short_v1: actualizado hace 45.8 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1620 | -0.7 |
| binance_perp/depth_snapshots | 20 | 2.3 |
| binance_perp/forced_liquidations | 59 | -0.0 |
| binance_perp/futures_market_metrics | 60 | -0.0 |
| binance_perp/futures_open_interest | 60 | -0.0 |
| binance_perp/futures_positioning | 61 | -0.7 |
| binance_perp/orderbook_l2_depth | 155 | -1.0 |
| binance_perp/trade_ticks | 104 | -1.0 |
| deribit/bbo_ticks | 61 | -1.0 |
| deribit/deribit_metrics | 65 | -1.0 |
| deribit/trade_ticks | 56 | -1.0 |
| dexscreener/token_boosts | 5 | 16.2 |
| dexscreener/token_prices | 60 | -0.9 |
| dexscreener/token_profiles | 20 | 0.1 |
| limitless/limitless_book | 61 | -0.9 |
| limitless/limitless_markets | 13 | 0.1 |
| polymarket/bbo_ticks | 1100 | -1.9 |
| polymarket/orderbook_l2_depth | 61 | -1.0 |
| polymarket/polymarket_metadata_history | 15 | -0.0 |
| polymarket/trade_ticks | 51 | -1.0 |
| pumpfun/creator_funding | 61 | -1.9 |
| pumpfun/pumpfun_completes | 28 | 1.1 |
| pumpfun/pumpfun_creates | 62 | -1.9 |
| pumpfun/pumpfun_trades | 62 | -1.9 |
| pumpfun/x_mentions | 0 | 9386.9 |
| telegram/calls | 12 | -1.9 |

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
{"timestamp_utc": "2026-10-13T13:40:14Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T13:40:18Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T13:41:06Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T13:41:22Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T13:41:29Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T13:41:36Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T13:41:42Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T13:41:47Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.