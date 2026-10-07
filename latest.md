# Snapshot Quant OS — 2026-10-07 08:51 UTC

## Polymarket up/down (paper)

- Señales 227 · llenadas 155 · perdidas 71 (31% se las llevó otro)
- PnL Binance US$ 1168.42 · PnL oficial US$ 0.00 (0 resueltas) · aciertos 0% · t por ventana None
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
- poly_updown: actualizado hace 0.4 min
- pump_azar: actualizado hace 446.9 min
- pump_billeteras: actualizado hace 446.9 min
- pump_billeteras_2x: actualizado hace 446.9 min
- pump_billeteras_azar: actualizado hace 446.9 min
- pump_detector_tarde: actualizado hace 446.9 min
- pump_grupo: actualizado hace 446.9 min
- pump_grupo_aguantar: actualizado hace 446.9 min
- pump_grupo_nicho: actualizado hace 446.9 min
- pump_nicho: actualizado hace 446.9 min
- pump_nicho_azar: actualizado hace 446.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1039 | -0.0 |
| binance_perp/depth_snapshots | 18 | 5.9 |
| binance_perp/forced_liquidations | 59 | -0.0 |
| binance_perp/futures_market_metrics | 59 | -0.0 |
| binance_perp/futures_open_interest | 60 | -0.0 |
| binance_perp/orderbook_l2_depth | 128 | -0.0 |
| binance_perp/trade_ticks | 63 | -0.0 |
| deribit/bbo_ticks | 55 | -0.0 |
| deribit/deribit_metrics | 60 | -0.0 |
| deribit/trade_ticks | 60 | -0.0 |
| dexscreener/token_boosts | 2 | 41.5 |
| dexscreener/token_prices | 10 | 6.8 |
| dexscreener/token_profiles | 6 | 6.8 |
| limitless/limitless_book | 37 | 5.3 |
| limitless/limitless_markets | 9 | 9.3 |
| polymarket/bbo_ticks | 518 | -0.0 |
| polymarket/orderbook_l2_depth | 60 | -0.0 |
| polymarket/polymarket_metadata_history | 16 | -0.0 |
| polymarket/trade_ticks | 53 | -0.0 |
| pumpfun/creator_funding | 26 | 1.5 |
| pumpfun/pumpfun_completes | 17 | 3.9 |
| pumpfun/pumpfun_creates | 46 | 0.3 |
| pumpfun/pumpfun_trades | 45 | 0.3 |
| pumpfun/x_mentions | 0 | 446.9 |
| telegram/calls | 9 | 3.8 |

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
{"timestamp_utc": "2026-10-07T08:43:52Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T08:45:12Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T08:45:22Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T08:47:16Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T08:48:06Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T08:49:59Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T08:51:03Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T08:51:10Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
```
### recorder.log
```
{"timestamp_utc": "2026-10-07T08:48:22Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
{"timestamp_utc": "2026-10-07T08:48:56Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T08:49:21Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T08:49:33Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T08:50:07Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T08:50:27Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T08:50:40Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T08:51:16Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
```

Detalle completo en latest.json.