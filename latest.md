# Snapshot Quant OS — 2026-10-14 03:51 UTC

## Polymarket up/down (paper)

- Señales 425 · llenadas 291 · perdidas 134 (32% se las llevó otro)
- PnL Binance US$ 1817.40 · PnL oficial US$ -84.10 (291 resueltas) · aciertos 40% · t por ventana -0.8387298218090913
- Criterio: todavía no

## Salud

- api: NEVER_STARTED
- web: NEVER_STARTED
- os_launcher: NEVER_STARTED
- supervisor: NEVER_STARTED
- markets_recorder: NEVER_STARTED
- paper_runtime: STOPPED
- pumpfun_recorder: DISABLED
- pumpfun_paper: DISABLED
- leader_paper: STOPPED
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 184.4 min
- btc_tendencia: actualizado hace 184.4 min
- carry_funding: actualizado hace 184.4 min
- combinada: actualizado hace 184.4 min
- examen_2x: actualizado hace 385.3 min
- flujo_7d: actualizado hace 184.4 min
- flujo_reg200: actualizado hace 184.4 min
- flujo_sectorial: actualizado hace 184.4 min
- flujo_v1: actualizado hace 184.4 min
- lider_azar: actualizado hace 184.4 min
- lider_corto: actualizado hace 184.4 min
- lider_sin_x: actualizado hace 184.4 min
- lider_x: actualizado hace 184.4 min
- mezcla_flujo_carry: actualizado hace 184.4 min
- poly_updown: actualizado hace 9346.8 min
- unlock_short_v1: actualizado hace 225.3 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 0 | 183.5 |
| binance_perp/depth_snapshots | 0 | 184.6 |
| binance_perp/forced_liquidations | 0 | 184.0 |
| binance_perp/futures_market_metrics | 0 | 184.0 |
| binance_perp/futures_open_interest | 0 | 184.0 |
| binance_perp/futures_positioning | 0 | 183.6 |
| binance_perp/orderbook_l2_depth | 0 | 184.0 |
| binance_perp/trade_ticks | 0 | 184.0 |
| deribit/bbo_ticks | 0 | 384.7 |
| deribit/deribit_metrics | 0 | 384.7 |
| deribit/trade_ticks | 0 | 385.7 |
| dexscreener/token_boosts | 0 | 391.9 |
| dexscreener/token_prices | 0 | 384.9 |
| dexscreener/token_profiles | 0 | 386.9 |
| limitless/limitless_book | 0 | 384.9 |
| limitless/limitless_markets | 0 | 384.9 |
| polymarket/bbo_ticks | 0 | 384.7 |
| polymarket/orderbook_l2_depth | 0 | 384.7 |
| polymarket/polymarket_metadata_history | 0 | 385.8 |
| polymarket/trade_ticks | 0 | 384.7 |
| pumpfun/creator_funding | 0 | 384.9 |
| pumpfun/pumpfun_completes | 0 | 384.9 |
| pumpfun/pumpfun_creates | 0 | 384.9 |
| pumpfun/pumpfun_trades | 0 | 384.9 |
| pumpfun/x_mentions | 0 | 10226.9 |
| telegram/calls | 0 | 385.9 |

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
{"timestamp_utc": "2026-10-14T00:17:15Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:20:23Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:30:25Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:30:34Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:31:13Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:32:30Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:35:16Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:37:16Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.