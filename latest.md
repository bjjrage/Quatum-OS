# Snapshot Quant OS — 2026-10-07 20:51 UTC

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

- baja_vol: actualizado hace 1.7 min
- btc_tendencia: actualizado hace 1.7 min
- carry_funding: actualizado hace 1.7 min
- combinada: actualizado hace 1.7 min
- examen_2x: actualizado hace 1.7 min
- flujo_7d: actualizado hace 1.7 min
- flujo_v1: actualizado hace 1.7 min
- lider_azar: actualizado hace 1.7 min
- lider_corto: actualizado hace 1.7 min
- lider_sin_x: actualizado hace 1.7 min
- lider_x: actualizado hace 1.7 min
- poly_updown: actualizado hace 286.8 min
- pump_azar: actualizado hace 1166.9 min
- pump_billeteras: actualizado hace 1166.9 min
- pump_billeteras_2x: actualizado hace 1166.9 min
- pump_billeteras_azar: actualizado hace 1166.9 min
- pump_detector_tarde: actualizado hace 1166.9 min
- pump_grupo: actualizado hace 1166.9 min
- pump_grupo_aguantar: actualizado hace 1166.9 min
- pump_grupo_nicho: actualizado hace 1166.9 min
- pump_nicho: actualizado hace 1166.9 min
- pump_nicho_azar: actualizado hace 1166.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 750 | 0.4 |
| binance_perp/depth_snapshots | 18 | 0.3 |
| binance_perp/forced_liquidations | 58 | 0.4 |
| binance_perp/futures_market_metrics | 59 | 0.4 |
| binance_perp/futures_open_interest | 60 | 0.4 |
| binance_perp/orderbook_l2_depth | 121 | 0.4 |
| binance_perp/trade_ticks | 61 | 0.4 |
| deribit/bbo_ticks | 60 | 0.4 |
| deribit/deribit_metrics | 60 | 0.4 |
| deribit/trade_ticks | 48 | 0.4 |
| dexscreener/token_boosts | 2 | 54.0 |
| dexscreener/token_prices | 9 | 50.0 |
| dexscreener/token_profiles | 21 | -0.1 |
| limitless/limitless_book | 60 | -0.1 |
| limitless/limitless_markets | 12 | -0.1 |
| polymarket/bbo_ticks | 511 | -0.2 |
| polymarket/orderbook_l2_depth | 60 | 0.4 |
| polymarket/polymarket_metadata_history | 17 | 0.4 |
| polymarket/trade_ticks | 51 | 0.4 |
| pumpfun/creator_funding | 60 | -0.1 |
| pumpfun/pumpfun_completes | 40 | -0.1 |
| pumpfun/pumpfun_creates | 60 | -0.1 |
| pumpfun/pumpfun_trades | 67 | -0.1 |
| pumpfun/x_mentions | 0 | 1166.9 |
| telegram/calls | 16 | 1.9 |

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
{"timestamp_utc": "2026-10-07T20:26:22Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T20:41:02Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T20:50:35Z", "level": "WARNING", "logger": "binance_oi_poller", "message": "Recorded stale Open Interest for NEARUSDT due to polling failure."}
{"timestamp_utc": "2026-10-07T20:50:39Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T20:50:48Z", "level": "WARNING", "logger": "binance_oi_poller", "message": "Recorded stale Open Interest for SUIUSDT due to polling failure."}
{"timestamp_utc": "2026-10-07T20:50:50Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-07T20:50:55Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T20:50:59Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
```

Detalle completo en latest.json.