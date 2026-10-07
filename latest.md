# Snapshot Quant OS — 2026-10-07 09:51 UTC

## Polymarket up/down (paper)

- Señales 273 · llenadas 184 · perdidas 87 (32% se las llevó otro)
- PnL Binance US$ 1427.67 · PnL oficial US$ 0.00 (0 resueltas) · aciertos 0% · t por ventana None
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

- baja_vol: actualizado hace 1.3 min
- btc_tendencia: actualizado hace 1.3 min
- carry_funding: actualizado hace 1.3 min
- combinada: actualizado hace 1.3 min
- examen_2x: actualizado hace 1.3 min
- flujo_7d: actualizado hace 1.3 min
- flujo_v1: actualizado hace 1.3 min
- lider_azar: actualizado hace 1.3 min
- lider_corto: actualizado hace 1.3 min
- lider_sin_x: actualizado hace 1.3 min
- lider_x: actualizado hace 1.3 min
- poly_updown: actualizado hace 0.3 min
- pump_azar: actualizado hace 506.9 min
- pump_billeteras: actualizado hace 506.9 min
- pump_billeteras_2x: actualizado hace 506.9 min
- pump_billeteras_azar: actualizado hace 506.9 min
- pump_detector_tarde: actualizado hace 506.9 min
- pump_grupo: actualizado hace 506.9 min
- pump_grupo_aguantar: actualizado hace 506.9 min
- pump_grupo_nicho: actualizado hace 506.9 min
- pump_nicho: actualizado hace 506.9 min
- pump_nicho_azar: actualizado hace 506.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1163 | 0.0 |
| binance_perp/depth_snapshots | 20 | 0.9 |
| binance_perp/forced_liquidations | 59 | 0.7 |
| binance_perp/futures_market_metrics | 59 | 0.7 |
| binance_perp/futures_open_interest | 60 | 0.7 |
| binance_perp/orderbook_l2_depth | 139 | 0.1 |
| binance_perp/trade_ticks | 71 | 0.7 |
| deribit/bbo_ticks | 60 | 0.7 |
| deribit/deribit_metrics | 60 | 0.7 |
| deribit/trade_ticks | 60 | 0.7 |
| dexscreener/token_boosts | 2 | 12.5 |
| dexscreener/token_prices | 9 | 1.3 |
| dexscreener/token_profiles | 6 | 1.4 |
| limitless/limitless_book | 16 | 1.0 |
| limitless/limitless_markets | 8 | 4.0 |
| polymarket/bbo_ticks | 862 | -0.2 |
| polymarket/orderbook_l2_depth | 60 | 0.7 |
| polymarket/polymarket_metadata_history | 17 | 0.7 |
| polymarket/trade_ticks | 57 | 0.7 |
| pumpfun/creator_funding | 15 | 0.9 |
| pumpfun/pumpfun_completes | 15 | 5.1 |
| pumpfun/pumpfun_creates | 46 | -0.2 |
| pumpfun/pumpfun_trades | 46 | -0.2 |
| pumpfun/x_mentions | 0 | 506.9 |
| telegram/calls | 7 | 6.5 |

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
{"timestamp_utc": "2026-10-07T09:36:25Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T09:36:30Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T09:36:59Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T09:41:19Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T09:41:58Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T09:43:57Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T09:48:12Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T09:48:52Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
```
### recorder.log
```
{"timestamp_utc": "2026-10-07T09:46:59Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T09:47:45Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T09:47:56Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T09:48:23Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T09:48:39Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
{"timestamp_utc": "2026-10-07T09:49:56Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T09:51:14Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
{"timestamp_utc": "2026-10-07T09:51:14Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
```

Detalle completo en latest.json.