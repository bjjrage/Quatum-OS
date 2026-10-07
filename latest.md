# Snapshot Quant OS — 2026-10-07 04:49 UTC

## Polymarket up/down (paper)

- Señales 44 · llenadas 28 · perdidas 16 (36% se las llevó otro)
- PnL Binance US$ 144.19 · PnL oficial US$ 0.00 (0 resueltas) · aciertos 0% · t por ventana None
- Criterio: todavía no

## Salud

- api: STOPPED
- web: RUNNING
- os_launcher: RUNNING
- supervisor: RUNNING
- markets_recorder: RUNNING
- paper_runtime: RUNNING
- pumpfun_recorder: RUNNING
- pumpfun_paper: DEGRADED
- leader_paper: RUNNING
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 1.6 min
- btc_tendencia: actualizado hace 1.6 min
- carry_funding: actualizado hace 1.6 min
- combinada: actualizado hace 1.6 min
- examen_2x: actualizado hace 1.6 min
- flujo_7d: actualizado hace 1.6 min
- flujo_v1: actualizado hace 1.6 min
- lider_azar: actualizado hace 1.6 min
- lider_corto: actualizado hace 1.6 min
- lider_sin_x: actualizado hace 1.6 min
- lider_x: actualizado hace 1.6 min
- poly_updown: actualizado hace 0.2 min
- pump_azar: actualizado hace 205.2 min
- pump_billeteras: actualizado hace 205.2 min
- pump_billeteras_2x: actualizado hace 205.2 min
- pump_billeteras_azar: actualizado hace 205.2 min
- pump_detector_tarde: actualizado hace 205.2 min
- pump_grupo: actualizado hace 205.2 min
- pump_grupo_aguantar: actualizado hace 205.2 min
- pump_grupo_nicho: actualizado hace 205.2 min
- pump_nicho: actualizado hace 205.2 min
- pump_nicho_azar: actualizado hace 205.2 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 960 | 0.0 |
| binance_perp/depth_snapshots | 20 | 0.2 |
| binance_perp/forced_liquidations | 57 | 0.8 |
| binance_perp/futures_market_metrics | 58 | 0.8 |
| binance_perp/futures_open_interest | 58 | 0.8 |
| binance_perp/orderbook_l2_depth | 139 | 0.3 |
| binance_perp/trade_ticks | 66 | 0.8 |
| deribit/bbo_ticks | 58 | 0.8 |
| deribit/deribit_metrics | 58 | 0.8 |
| deribit/trade_ticks | 56 | -0.2 |
| dexscreener/token_boosts | 3 | 42.2 |
| dexscreener/token_prices | 9 | 9.8 |
| dexscreener/token_profiles | 7 | 9.8 |
| limitless/limitless_book | 34 | 0.4 |
| limitless/limitless_markets | 10 | 3.1 |
| polymarket/bbo_ticks | 478 | -0.2 |
| polymarket/orderbook_l2_depth | 59 | -0.2 |
| polymarket/polymarket_metadata_history | 16 | 3.8 |
| polymarket/trade_ticks | 47 | -0.2 |
| pumpfun/creator_funding | 23 | 1.7 |
| pumpfun/pumpfun_completes | 15 | 5.5 |
| pumpfun/pumpfun_creates | 45 | 0.5 |
| pumpfun/pumpfun_trades | 45 | 0.5 |
| pumpfun/x_mentions | 0 | 205.2 |
| telegram/calls | 3 | 5.5 |

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
{"timestamp_utc": "2026-10-07T04:38:31Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T04:38:52Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T04:40:15Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T04:40:25Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T04:41:23Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T04:41:47Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T04:42:28Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T04:48:20Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
```
### recorder.log
```
{"timestamp_utc": "2026-10-07T04:44:42Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T04:45:39Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T04:46:04Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
{"timestamp_utc": "2026-10-07T04:46:36Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T04:47:37Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T04:48:36Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T04:48:57Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T04:49:05Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
```

Detalle completo en latest.json.