# Snapshot Quant OS — 2026-10-13 17:51 UTC

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

- baja_vol: actualizado hace 0.3 min
- btc_tendencia: actualizado hace 0.3 min
- carry_funding: actualizado hace 0.3 min
- combinada: actualizado hace 0.3 min
- examen_2x: actualizado hace 0.3 min
- flujo_7d: actualizado hace 0.3 min
- flujo_reg200: actualizado hace 0.3 min
- flujo_sectorial: actualizado hace 0.3 min
- flujo_v1: actualizado hace 0.3 min
- lider_azar: actualizado hace 0.3 min
- lider_corto: actualizado hace 0.3 min
- lider_sin_x: actualizado hace 0.3 min
- lider_x: actualizado hace 0.3 min
- mezcla_flujo_carry: actualizado hace 0.3 min
- poly_updown: actualizado hace 8746.8 min
- unlock_short_v1: actualizado hace 45.7 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1137 | -0.9 |
| binance_perp/depth_snapshots | 17 | 1.1 |
| binance_perp/forced_liquidations | 59 | -0.7 |
| binance_perp/futures_market_metrics | 60 | -0.7 |
| binance_perp/futures_open_interest | 61 | -0.7 |
| binance_perp/futures_positioning | 61 | -0.9 |
| binance_perp/orderbook_l2_depth | 141 | -1.2 |
| binance_perp/trade_ticks | 63 | -0.7 |
| deribit/bbo_ticks | 61 | -0.7 |
| deribit/deribit_metrics | 61 | -0.7 |
| deribit/trade_ticks | 59 | -0.7 |
| dexscreener/token_boosts | 8 | 12.5 |
| dexscreener/token_prices | 61 | -0.6 |
| dexscreener/token_profiles | 22 | 0.4 |
| limitless/limitless_book | 61 | -0.6 |
| limitless/limitless_markets | 13 | 0.4 |
| polymarket/bbo_ticks | 915 | -1.9 |
| polymarket/orderbook_l2_depth | 62 | -1.7 |
| polymarket/polymarket_metadata_history | 13 | -0.7 |
| polymarket/trade_ticks | 59 | -1.7 |
| pumpfun/creator_funding | 62 | -1.6 |
| pumpfun/pumpfun_completes | 41 | -1.6 |
| pumpfun/pumpfun_creates | 62 | -1.6 |
| pumpfun/pumpfun_trades | 63 | -1.6 |
| pumpfun/x_mentions | 0 | 9627.0 |
| telegram/calls | 15 | -0.6 |

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
{"timestamp_utc": "2026-10-13T17:30:39Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T17:32:12Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-13T17:37:04Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T17:40:04Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T17:50:41Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T17:51:11Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T17:52:21Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T17:52:29Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.