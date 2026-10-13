# Snapshot Quant OS — 2026-10-13 10:51 UTC

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
- flujo_reg200: actualizado hace 1.0 min
- flujo_sectorial: actualizado hace 1.0 min
- flujo_v1: actualizado hace 1.0 min
- lider_azar: actualizado hace 1.0 min
- lider_corto: actualizado hace 1.0 min
- lider_sin_x: actualizado hace 1.0 min
- lider_x: actualizado hace 1.0 min
- mezcla_flujo_carry: actualizado hace 1.0 min
- poly_updown: actualizado hace 8326.8 min
- unlock_short_v1: actualizado hace 45.8 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1215 | -0.8 |
| binance_perp/depth_snapshots | 19 | -0.6 |
| binance_perp/forced_liquidations | 60 | -0.9 |
| binance_perp/futures_market_metrics | 60 | -0.9 |
| binance_perp/futures_open_interest | 61 | -0.9 |
| binance_perp/futures_positioning | 61 | -0.6 |
| binance_perp/orderbook_l2_depth | 150 | -0.9 |
| binance_perp/trade_ticks | 67 | -0.9 |
| deribit/bbo_ticks | 43 | -0.9 |
| deribit/deribit_metrics | 61 | -0.9 |
| deribit/trade_ticks | 60 | -0.9 |
| dexscreener/token_boosts | 4 | 17.6 |
| dexscreener/token_prices | 60 | 0.6 |
| dexscreener/token_profiles | 9 | 7.6 |
| limitless/limitless_book | 61 | -0.4 |
| limitless/limitless_markets | 15 | -0.4 |
| polymarket/bbo_ticks | 462 | -1.5 |
| polymarket/orderbook_l2_depth | 61 | -0.9 |
| polymarket/polymarket_metadata_history | 14 | 0.1 |
| polymarket/trade_ticks | 57 | -0.9 |
| pumpfun/creator_funding | 60 | -1.4 |
| pumpfun/pumpfun_completes | 28 | -1.4 |
| pumpfun/pumpfun_creates | 62 | -1.4 |
| pumpfun/pumpfun_trades | 62 | -1.4 |
| pumpfun/x_mentions | 0 | 9206.9 |
| telegram/calls | 10 | 2.6 |

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
{"timestamp_utc": "2026-10-13T09:55:45Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 5.1s..."}
{"timestamp_utc": "2026-10-13T09:55:55Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T10:10:40Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T10:21:01Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T10:25:04Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T10:35:41Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T10:46:56Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T10:50:47Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
```

Detalle completo en latest.json.