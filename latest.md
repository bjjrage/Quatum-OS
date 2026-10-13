# Snapshot Quant OS — 2026-10-13 23:51 UTC

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
- pumpfun_recorder: DISABLED
- pumpfun_paper: DISABLED
- leader_paper: RUNNING
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 1.0 min
- btc_tendencia: actualizado hace 1.0 min
- carry_funding: actualizado hace 1.0 min
- combinada: actualizado hace 1.0 min
- examen_2x: actualizado hace 145.3 min
- flujo_7d: actualizado hace 1.0 min
- flujo_reg200: actualizado hace 1.0 min
- flujo_sectorial: actualizado hace 1.0 min
- flujo_v1: actualizado hace 1.0 min
- lider_azar: actualizado hace 1.0 min
- lider_corto: actualizado hace 1.0 min
- lider_sin_x: actualizado hace 1.0 min
- lider_x: actualizado hace 1.0 min
- mezcla_flujo_carry: actualizado hace 1.0 min
- poly_updown: actualizado hace 9106.9 min
- unlock_short_v1: actualizado hace 45.3 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 686 | -1.1 |
| binance_perp/depth_snapshots | 18 | 2.6 |
| binance_perp/forced_liquidations | 56 | 0.2 |
| binance_perp/futures_market_metrics | 61 | -0.8 |
| binance_perp/futures_open_interest | 61 | -0.8 |
| binance_perp/futures_positioning | 60 | -0.4 |
| binance_perp/orderbook_l2_depth | 120 | -1.4 |
| binance_perp/trade_ticks | 63 | -0.8 |
| deribit/bbo_ticks | 0 | 144.7 |
| deribit/deribit_metrics | 0 | 144.7 |
| deribit/trade_ticks | 0 | 145.7 |
| dexscreener/token_boosts | 0 | 151.9 |
| dexscreener/token_prices | 0 | 144.9 |
| dexscreener/token_profiles | 0 | 146.9 |
| limitless/limitless_book | 0 | 144.9 |
| limitless/limitless_markets | 0 | 144.9 |
| polymarket/bbo_ticks | 0 | 144.7 |
| polymarket/orderbook_l2_depth | 0 | 144.7 |
| polymarket/polymarket_metadata_history | 0 | 145.8 |
| polymarket/trade_ticks | 0 | 144.7 |
| pumpfun/creator_funding | 0 | 144.9 |
| pumpfun/pumpfun_completes | 0 | 144.9 |
| pumpfun/pumpfun_creates | 0 | 144.9 |
| pumpfun/pumpfun_trades | 0 | 144.9 |
| pumpfun/x_mentions | 0 | 9987.0 |
| telegram/calls | 0 | 145.9 |

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
{"timestamp_utc": "2026-10-13T22:55:10Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T22:55:14Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-13T22:55:42Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T22:55:46Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-13T22:56:06Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T23:02:21Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T23:03:29Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T23:04:28Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.