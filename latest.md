# Snapshot Quant OS — 2026-10-07 15:51 UTC

## Polymarket up/down (paper)

- Señales 416 · llenadas 285 · perdidas 131 (31% se las llevó otro)
- PnL Binance US$ 1821.92 · PnL oficial US$ 0.00 (0 resueltas) · aciertos 0% · t por ventana None
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

- baja_vol: actualizado hace 0.4 min
- btc_tendencia: actualizado hace 0.4 min
- carry_funding: actualizado hace 0.4 min
- combinada: actualizado hace 0.4 min
- examen_2x: actualizado hace 0.4 min
- flujo_7d: actualizado hace 0.4 min
- flujo_v1: actualizado hace 0.4 min
- lider_azar: actualizado hace 0.4 min
- lider_corto: actualizado hace 0.4 min
- lider_sin_x: actualizado hace 0.4 min
- lider_x: actualizado hace 0.4 min
- poly_updown: actualizado hace 0.2 min
- pump_azar: actualizado hace 866.9 min
- pump_billeteras: actualizado hace 866.9 min
- pump_billeteras_2x: actualizado hace 866.9 min
- pump_billeteras_azar: actualizado hace 866.9 min
- pump_detector_tarde: actualizado hace 866.9 min
- pump_grupo: actualizado hace 866.9 min
- pump_grupo_aguantar: actualizado hace 866.9 min
- pump_grupo_nicho: actualizado hace 866.9 min
- pump_nicho: actualizado hace 866.9 min
- pump_nicho_azar: actualizado hace 866.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1217 | -0.2 |
| binance_perp/depth_snapshots | 24 | -0.2 |
| binance_perp/forced_liquidations | 58 | 0.4 |
| binance_perp/futures_market_metrics | 58 | 0.4 |
| binance_perp/futures_open_interest | 60 | 0.4 |
| binance_perp/orderbook_l2_depth | 135 | -0.5 |
| binance_perp/trade_ticks | 75 | 0.4 |
| deribit/bbo_ticks | 61 | -0.6 |
| deribit/deribit_metrics | 61 | -0.6 |
| deribit/trade_ticks | 57 | -0.6 |
| dexscreener/token_boosts | 4 | 21.1 |
| dexscreener/token_prices | 33 | -0.8 |
| dexscreener/token_profiles | 16 | -0.7 |
| limitless/limitless_book | 29 | 9.5 |
| limitless/limitless_markets | 10 | 8.1 |
| polymarket/bbo_ticks | 673 | -1.0 |
| polymarket/orderbook_l2_depth | 61 | -0.6 |
| polymarket/polymarket_metadata_history | 17 | 0.4 |
| polymarket/trade_ticks | 56 | -0.6 |
| pumpfun/creator_funding | 24 | 0.5 |
| pumpfun/pumpfun_completes | 10 | -1.0 |
| pumpfun/pumpfun_creates | 42 | -0.9 |
| pumpfun/pumpfun_trades | 45 | -0.8 |
| pumpfun/x_mentions | 0 | 866.9 |
| telegram/calls | 17 | -1.1 |

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
{"timestamp_utc": "2026-10-07T15:48:30Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T15:49:00Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T15:49:05Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T15:50:19Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T15:51:43Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T15:51:49Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T15:51:54Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T15:52:01Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
```
### recorder.log
```
{"timestamp_utc": "2026-10-07T15:48:58Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T15:49:36Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T15:50:11Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T15:50:14Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T15:50:59Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
{"timestamp_utc": "2026-10-07T15:50:59Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T15:51:10Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener respondi\u00f3 404 en dexscreener.com"}
{"timestamp_utc": "2026-10-07T15:51:37Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
```

Detalle completo en latest.json.