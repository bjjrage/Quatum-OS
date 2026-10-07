# Snapshot Quant OS — 2026-10-07 22:31 UTC

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
- flujo_v1: actualizado hace 0.0 min
- lider_azar: actualizado hace 0.0 min
- lider_corto: actualizado hace 0.0 min
- lider_sin_x: actualizado hace 0.0 min
- lider_x: actualizado hace 0.0 min
- poly_updown: actualizado hace 386.9 min
- pump_azar: actualizado hace 1267.0 min
- pump_billeteras: actualizado hace 1267.1 min
- pump_billeteras_2x: actualizado hace 1267.1 min
- pump_billeteras_azar: actualizado hace 1267.0 min
- pump_detector_tarde: actualizado hace 1267.0 min
- pump_grupo: actualizado hace 1267.0 min
- pump_grupo_aguantar: actualizado hace 1267.0 min
- pump_grupo_nicho: actualizado hace 1267.0 min
- pump_nicho: actualizado hace 1267.0 min
- pump_nicho_azar: actualizado hace 1267.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 680 | -0.3 |
| binance_perp/depth_snapshots | 18 | 3.3 |
| binance_perp/forced_liquidations | 57 | -0.0 |
| binance_perp/futures_market_metrics | 60 | -0.0 |
| binance_perp/futures_open_interest | 60 | -0.0 |
| binance_perp/orderbook_l2_depth | 115 | -0.0 |
| binance_perp/trade_ticks | 60 | -0.0 |
| deribit/bbo_ticks | 60 | -0.0 |
| deribit/deribit_metrics | 60 | -0.0 |
| deribit/trade_ticks | 44 | 2.0 |
| dexscreener/token_boosts | 2 | -0.3 |
| dexscreener/token_prices | 61 | -0.3 |
| dexscreener/token_profiles | 18 | 10.8 |
| limitless/limitless_book | 61 | -0.3 |
| limitless/limitless_markets | 13 | 0.7 |
| polymarket/bbo_ticks | 351 | -0.6 |
| polymarket/orderbook_l2_depth | 60 | -0.0 |
| polymarket/polymarket_metadata_history | 17 | -0.0 |
| polymarket/trade_ticks | 39 | -0.0 |
| pumpfun/creator_funding | 61 | -0.3 |
| pumpfun/pumpfun_completes | 44 | -0.3 |
| pumpfun/pumpfun_creates | 61 | -0.3 |
| pumpfun/pumpfun_trades | 67 | -0.3 |
| pumpfun/x_mentions | 0 | 1267.0 |
| telegram/calls | 11 | -0.3 |

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
{"timestamp_utc": "2026-10-07T22:14:17Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-07T22:16:18Z", "level": "WARNING", "logger": "binance_oi_poller", "message": "Recorded stale Open Interest for BTCUSDT due to polling failure."}
{"timestamp_utc": "2026-10-07T22:16:34Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T22:16:51Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T22:17:20Z", "level": "WARNING", "logger": "binance_oi_poller", "message": "Recorded stale Open Interest for ETHUSDT due to polling failure."}
{"timestamp_utc": "2026-10-07T22:17:32Z", "level": "WARNING", "logger": "binance_oi_poller", "message": "Recorded stale Open Interest for SOLUSDT due to polling failure."}
{"timestamp_utc": "2026-10-07T22:17:36Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T22:20:20Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.