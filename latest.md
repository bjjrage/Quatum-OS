# Snapshot Quant OS — 2026-10-13 11:51 UTC

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

- baja_vol: actualizado hace 1.7 min
- btc_tendencia: actualizado hace 1.7 min
- carry_funding: actualizado hace 1.7 min
- combinada: actualizado hace 1.7 min
- examen_2x: actualizado hace 1.7 min
- flujo_7d: actualizado hace 1.7 min
- flujo_reg200: actualizado hace 1.7 min
- flujo_sectorial: actualizado hace 1.7 min
- flujo_v1: actualizado hace 1.7 min
- lider_azar: actualizado hace 1.7 min
- lider_corto: actualizado hace 1.7 min
- lider_sin_x: actualizado hace 1.7 min
- lider_x: actualizado hace 1.7 min
- mezcla_flujo_carry: actualizado hace 1.7 min
- poly_updown: actualizado hace 8386.8 min
- unlock_short_v1: actualizado hace 45.8 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1613 | -0.6 |
| binance_perp/depth_snapshots | 18 | 0.4 |
| binance_perp/forced_liquidations | 59 | -0.3 |
| binance_perp/futures_market_metrics | 59 | -0.3 |
| binance_perp/futures_open_interest | 60 | -0.3 |
| binance_perp/futures_positioning | 61 | -0.6 |
| binance_perp/orderbook_l2_depth | 161 | -0.8 |
| binance_perp/trade_ticks | 105 | -0.3 |
| deribit/bbo_ticks | 60 | -0.3 |
| deribit/deribit_metrics | 63 | -0.3 |
| deribit/trade_ticks | 57 | -0.3 |
| dexscreener/token_boosts | 3 | 7.4 |
| dexscreener/token_prices | 60 | -0.6 |
| dexscreener/token_profiles | 14 | 0.4 |
| limitless/limitless_book | 61 | -0.6 |
| limitless/limitless_markets | 13 | 0.4 |
| polymarket/bbo_ticks | 805 | -1.5 |
| polymarket/orderbook_l2_depth | 61 | -1.3 |
| polymarket/polymarket_metadata_history | 12 | -0.3 |
| polymarket/trade_ticks | 53 | -1.3 |
| pumpfun/creator_funding | 61 | -0.6 |
| pumpfun/pumpfun_completes | 29 | -1.6 |
| pumpfun/pumpfun_creates | 62 | -1.6 |
| pumpfun/pumpfun_trades | 62 | -1.6 |
| pumpfun/x_mentions | 0 | 9266.9 |
| telegram/calls | 14 | -0.6 |

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
{"timestamp_utc": "2026-10-13T11:30:19Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T11:30:22Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-13T11:30:25Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T11:30:29Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T11:30:33Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T11:30:37Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T11:30:37Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T11:43:59Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.