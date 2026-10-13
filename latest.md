# Snapshot Quant OS — 2026-10-13 14:51 UTC

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

- baja_vol: actualizado hace 0.7 min
- btc_tendencia: actualizado hace 0.7 min
- carry_funding: actualizado hace 0.7 min
- combinada: actualizado hace 0.7 min
- examen_2x: actualizado hace 0.7 min
- flujo_7d: actualizado hace 0.7 min
- flujo_reg200: actualizado hace 0.7 min
- flujo_sectorial: actualizado hace 0.7 min
- flujo_v1: actualizado hace 0.7 min
- lider_azar: actualizado hace 0.7 min
- lider_corto: actualizado hace 0.7 min
- lider_sin_x: actualizado hace 0.7 min
- lider_x: actualizado hace 0.7 min
- mezcla_flujo_carry: actualizado hace 0.7 min
- poly_updown: actualizado hace 8566.9 min
- unlock_short_v1: actualizado hace 34.8 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1888 | -1.1 |
| binance_perp/depth_snapshots | 19 | -0.7 |
| binance_perp/forced_liquidations | 61 | -0.4 |
| binance_perp/futures_market_metrics | 61 | -0.4 |
| binance_perp/futures_open_interest | 61 | -0.4 |
| binance_perp/futures_positioning | 61 | -0.7 |
| binance_perp/orderbook_l2_depth | 159 | -1.4 |
| binance_perp/trade_ticks | 108 | -1.4 |
| deribit/bbo_ticks | 62 | -1.4 |
| deribit/deribit_metrics | 62 | -1.4 |
| deribit/trade_ticks | 61 | -1.4 |
| dexscreener/token_boosts | 6 | 9.0 |
| dexscreener/token_prices | 59 | -1.0 |
| dexscreener/token_profiles | 21 | -1.0 |
| limitless/limitless_book | 61 | -1.0 |
| limitless/limitless_markets | 12 | -0.0 |
| polymarket/bbo_ticks | 1256 | -2.4 |
| polymarket/orderbook_l2_depth | 63 | -2.4 |
| polymarket/polymarket_metadata_history | 13 | -0.4 |
| polymarket/trade_ticks | 52 | -0.4 |
| pumpfun/creator_funding | 62 | -2.0 |
| pumpfun/pumpfun_completes | 29 | -1.0 |
| pumpfun/pumpfun_creates | 63 | -3.0 |
| pumpfun/pumpfun_trades | 64 | -3.0 |
| pumpfun/x_mentions | 0 | 9447.0 |
| telegram/calls | 14 | 1.0 |

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
{"timestamp_utc": "2026-10-13T14:27:31Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T14:31:18Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T14:37:08Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T14:37:12Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T14:37:41Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T14:41:22Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T14:41:58Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T14:50:51Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.