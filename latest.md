# Snapshot Quant OS — 2026-10-07 16:21 UTC

## Polymarket up/down (paper)

- Señales 425 · llenadas 291 · perdidas 134 (32% se las llevó otro)
- PnL Binance US$ 1817.40 · PnL oficial US$ 0.00 (0 resueltas) · aciertos 0% · t por ventana None
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

- baja_vol: actualizado hace 0.9 min
- btc_tendencia: actualizado hace 0.9 min
- carry_funding: actualizado hace 0.9 min
- combinada: actualizado hace 0.9 min
- examen_2x: actualizado hace 0.9 min
- flujo_7d: actualizado hace 0.9 min
- flujo_v1: actualizado hace 0.9 min
- lider_azar: actualizado hace 0.9 min
- lider_corto: actualizado hace 0.9 min
- lider_sin_x: actualizado hace 0.9 min
- lider_x: actualizado hace 0.9 min
- poly_updown: actualizado hace 17.3 min
- pump_azar: actualizado hace 897.4 min
- pump_billeteras: actualizado hace 897.4 min
- pump_billeteras_2x: actualizado hace 897.4 min
- pump_billeteras_azar: actualizado hace 897.4 min
- pump_detector_tarde: actualizado hace 897.4 min
- pump_grupo: actualizado hace 897.4 min
- pump_grupo_aguantar: actualizado hace 897.4 min
- pump_grupo_nicho: actualizado hace 897.4 min
- pump_nicho: actualizado hace 897.4 min
- pump_nicho_azar: actualizado hace 897.4 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1083 | -0.1 |
| binance_perp/depth_snapshots | 20 | 4.8 |
| binance_perp/forced_liquidations | 58 | 0.7 |
| binance_perp/futures_market_metrics | 58 | 0.7 |
| binance_perp/futures_open_interest | 59 | 0.7 |
| binance_perp/orderbook_l2_depth | 128 | 0.2 |
| binance_perp/trade_ticks | 73 | 0.7 |
| deribit/bbo_ticks | 59 | 0.7 |
| deribit/deribit_metrics | 59 | 0.7 |
| deribit/trade_ticks | 55 | 0.7 |
| dexscreener/token_boosts | 6 | 11.8 |
| dexscreener/token_prices | 39 | -0.3 |
| dexscreener/token_profiles | 21 | 0.7 |
| limitless/limitless_book | 37 | -0.3 |
| limitless/limitless_markets | 13 | -0.3 |
| polymarket/bbo_ticks | 659 | -0.3 |
| polymarket/orderbook_l2_depth | 60 | -0.3 |
| polymarket/polymarket_metadata_history | 16 | 0.7 |
| polymarket/trade_ticks | 58 | -0.3 |
| pumpfun/creator_funding | 28 | -0.3 |
| pumpfun/pumpfun_completes | 14 | 2.7 |
| pumpfun/pumpfun_creates | 46 | -0.3 |
| pumpfun/pumpfun_trades | 49 | -0.3 |
| pumpfun/x_mentions | 0 | 897.4 |
| telegram/calls | 18 | -0.3 |

## Problemas en logs (últimos)

### api.log
```
{"timestamp_utc": "2026-10-06T00:01:40Z", "level": "ERROR", "logger": "flujo_paper", "message": "state.json ilegible: NO se sobrescribe; revisar a mano."}
{"timestamp_utc": "2026-10-06T00:01:40Z", "level": "ERROR", "logger": "flujo_paper", "message": "state.json ilegible: NO se sobrescribe; revisar a mano."}
{"timestamp_utc": "2026-10-06T00:01:40Z", "level": "ERROR", "logger": "flujo_paper", "message": "state.json ilegible: NO se sobrescribe; revisar a mano."}
{"timestamp_utc": "2026-10-06T00:01:40Z", "level": "ERROR", "logger": "flujo_paper", "message": "state.json ilegible: NO se sobrescribe; revisar a mano."}
{"timestamp_utc": "2026-10-06T00:01:40Z", "level": "ERROR", "logger": "flujo_paper", "message": "state.json ilegible: NO se sobrescribe; revisar a mano."}
{"timestamp_utc": "2026-10-06T00:01:40Z", "level": "ERROR", "logger": "flujo_paper", "message": "state.json ilegible: NO se sobrescribe; revisar a mano."}
{"timestamp_utc": "2026-10-06T00:01:40Z", "level": "ERROR", "logger": "flujo_paper", "message": "state.json ilegible: NO se sobrescribe; revisar a mano."}
{"timestamp_utc": "2026-10-06T00:01:40Z", "level": "ERROR", "logger": "flujo_paper", "message": "state.json ilegible: NO se sobrescribe; revisar a mano."}
```
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
{"timestamp_utc": "2026-10-07T16:06:20Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:06:33Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:06:37Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:07:05Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:07:27Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:07:32Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:07:43Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:15:22Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.