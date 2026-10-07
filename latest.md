# Snapshot Quant OS — 2026-10-07 16:51 UTC

## Polymarket up/down (paper)

- Señales 425 · llenadas 291 · perdidas 134 (32% se las llevó otro)
- PnL Binance US$ 1817.40 · PnL oficial US$ 0.00 (0 resueltas) · aciertos 0% · t por ventana None
- Criterio: todavía no

## Salud

- api: STOPPED
- web: ERROR
- os_launcher: RUNNING
- supervisor: ERROR
- markets_recorder: STOPPED
- paper_runtime: ERROR
- pumpfun_recorder: STOPPED
- pumpfun_paper: DISABLED
- leader_paper: STOPPED
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 15.6 min
- btc_tendencia: actualizado hace 15.6 min
- carry_funding: actualizado hace 15.6 min
- combinada: actualizado hace 15.6 min
- examen_2x: actualizado hace 15.6 min
- flujo_7d: actualizado hace 15.6 min
- flujo_v1: actualizado hace 15.6 min
- lider_azar: actualizado hace 15.6 min
- lider_corto: actualizado hace 15.6 min
- lider_sin_x: actualizado hace 15.6 min
- lider_x: actualizado hace 15.6 min
- poly_updown: actualizado hace 46.8 min
- pump_azar: actualizado hace 926.9 min
- pump_billeteras: actualizado hace 926.9 min
- pump_billeteras_2x: actualizado hace 926.9 min
- pump_billeteras_azar: actualizado hace 926.9 min
- pump_detector_tarde: actualizado hace 926.9 min
- pump_grupo: actualizado hace 926.9 min
- pump_grupo_aguantar: actualizado hace 926.9 min
- pump_grupo_nicho: actualizado hace 926.9 min
- pump_nicho: actualizado hace 926.9 min
- pump_nicho_azar: actualizado hace 926.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 829 | 14.7 |
| binance_perp/depth_snapshots | 16 | 16.3 |
| binance_perp/forced_liquidations | 44 | 15.2 |
| binance_perp/futures_market_metrics | 44 | 15.2 |
| binance_perp/futures_open_interest | 45 | 15.2 |
| binance_perp/orderbook_l2_depth | 101 | 15.2 |
| binance_perp/trade_ticks | 57 | 15.2 |
| deribit/bbo_ticks | 45 | 15.2 |
| deribit/deribit_metrics | 45 | 15.2 |
| deribit/trade_ticks | 42 | 16.2 |
| dexscreener/token_boosts | 5 | 19.3 |
| dexscreener/token_prices | 36 | 15.2 |
| dexscreener/token_profiles | 19 | 15.2 |
| limitless/limitless_book | 39 | 15.2 |
| limitless/limitless_markets | 11 | 20.3 |
| polymarket/bbo_ticks | 405 | 15.2 |
| polymarket/orderbook_l2_depth | 45 | 15.2 |
| polymarket/polymarket_metadata_history | 12 | 15.2 |
| polymarket/trade_ticks | 42 | 18.2 |
| pumpfun/creator_funding | 30 | 15.2 |
| pumpfun/pumpfun_completes | 20 | 17.2 |
| pumpfun/pumpfun_creates | 41 | 15.2 |
| pumpfun/pumpfun_trades | 42 | 15.2 |
| pumpfun/x_mentions | 0 | 926.9 |
| telegram/calls | 19 | 15.2 |

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
{"timestamp_utc": "2026-10-07T16:06:33Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:06:37Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:07:05Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:07:27Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:07:32Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:07:43Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:15:22Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T16:31:25Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.