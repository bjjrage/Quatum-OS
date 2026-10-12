# Snapshot Quant OS — 2026-10-12 20:51 UTC

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

- baja_vol: actualizado hace 0.0 min
- btc_tendencia: actualizado hace 0.0 min
- carry_funding: actualizado hace 0.0 min
- combinada: actualizado hace 0.0 min
- examen_2x: actualizado hace 0.0 min
- flujo_7d: actualizado hace 0.0 min
- flujo_reg200: actualizado hace 0.0 min
- flujo_sectorial: actualizado hace 0.0 min
- flujo_v1: actualizado hace 0.0 min
- lider_azar: actualizado hace 0.0 min
- lider_corto: actualizado hace 0.0 min
- lider_sin_x: actualizado hace 0.0 min
- lider_x: actualizado hace 0.0 min
- mezcla_flujo_carry: actualizado hace 0.0 min
- poly_updown: actualizado hace 7486.8 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 180 | -0.6 |
| binance_perp/depth_snapshots | 5 | 3.8 |
| binance_perp/forced_liquidations | 17 | -0.2 |
| binance_perp/futures_market_metrics | 17 | -0.2 |
| binance_perp/futures_open_interest | 17 | -0.2 |
| binance_perp/futures_positioning | 15 | -0.2 |
| binance_perp/orderbook_l2_depth | 35 | -0.8 |
| binance_perp/trade_ticks | 17 | -0.2 |
| deribit/bbo_ticks | 17 | -0.2 |
| deribit/deribit_metrics | 17 | -0.2 |
| deribit/trade_ticks | 6 | -0.2 |
| dexscreener/token_boosts | 1 | 15.8 |
| dexscreener/token_prices | 17 | -0.2 |
| dexscreener/token_profiles | 9 | 0.8 |
| limitless/limitless_book | 17 | -0.2 |
| limitless/limitless_markets | 5 | -0.2 |
| polymarket/bbo_ticks | 249 | -1.5 |
| polymarket/orderbook_l2_depth | 18 | -1.2 |
| polymarket/polymarket_metadata_history | 6 | -0.2 |
| polymarket/trade_ticks | 18 | -1.2 |
| pumpfun/creator_funding | 15 | -1.2 |
| pumpfun/pumpfun_completes | 10 | -1.2 |
| pumpfun/pumpfun_creates | 18 | -1.2 |
| pumpfun/pumpfun_trades | 20 | -1.2 |
| pumpfun/x_mentions | 0 | 8366.9 |
| telegram/calls | 2 | -0.2 |

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
{"timestamp_utc": "2026-10-12T17:02:24Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:03:27Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:03:42Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:04:16Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T17:07:42Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T20:34:16Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-12T20:35:22Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T20:50:48Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.