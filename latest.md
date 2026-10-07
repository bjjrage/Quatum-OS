# Snapshot Quant OS — 2026-10-07 05:51 UTC

## Polymarket up/down (paper)

- Señales 92 · llenadas 57 · perdidas 32 (35% se las llevó otro)
- PnL Binance US$ 470.85 · PnL oficial US$ 0.00 (0 resueltas) · aciertos 0% · t por ventana None
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

- baja_vol: actualizado hace 0.2 min
- btc_tendencia: actualizado hace 0.2 min
- carry_funding: actualizado hace 0.2 min
- combinada: actualizado hace 0.2 min
- examen_2x: actualizado hace 0.2 min
- flujo_7d: actualizado hace 0.2 min
- flujo_v1: actualizado hace 0.2 min
- lider_azar: actualizado hace 0.2 min
- lider_corto: actualizado hace 0.2 min
- lider_sin_x: actualizado hace 0.2 min
- lider_x: actualizado hace 0.2 min
- poly_updown: actualizado hace 0.5 min
- pump_azar: actualizado hace 266.9 min
- pump_billeteras: actualizado hace 266.9 min
- pump_billeteras_2x: actualizado hace 266.9 min
- pump_billeteras_azar: actualizado hace 266.9 min
- pump_detector_tarde: actualizado hace 266.9 min
- pump_grupo: actualizado hace 266.9 min
- pump_grupo_aguantar: actualizado hace 266.9 min
- pump_grupo_nicho: actualizado hace 266.9 min
- pump_nicho: actualizado hace 266.9 min
- pump_nicho_azar: actualizado hace 266.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 763 | -0.1 |
| binance_perp/depth_snapshots | 18 | 2.9 |
| binance_perp/forced_liquidations | 59 | 0.2 |
| binance_perp/futures_market_metrics | 60 | 0.2 |
| binance_perp/futures_open_interest | 60 | 0.2 |
| binance_perp/orderbook_l2_depth | 123 | 0.2 |
| binance_perp/trade_ticks | 60 | 0.2 |
| deribit/bbo_ticks | 60 | 0.2 |
| deribit/deribit_metrics | 60 | 0.2 |
| deribit/trade_ticks | 54 | 0.2 |
| dexscreener/token_boosts | 3 | 1.1 |
| dexscreener/token_prices | 10 | 1.0 |
| dexscreener/token_profiles | 7 | 1.0 |
| limitless/limitless_book | 28 | 0.8 |
| limitless/limitless_markets | 9 | 4.0 |
| polymarket/bbo_ticks | 540 | -0.2 |
| polymarket/orderbook_l2_depth | 60 | 0.2 |
| polymarket/polymarket_metadata_history | 16 | 0.2 |
| polymarket/trade_ticks | 58 | 0.2 |
| pumpfun/creator_funding | 19 | 0.7 |
| pumpfun/pumpfun_completes | 16 | 2.2 |
| pumpfun/pumpfun_creates | 45 | 0.9 |
| pumpfun/pumpfun_trades | 45 | 0.9 |
| pumpfun/x_mentions | 0 | 266.9 |
| telegram/calls | 9 | 3.6 |

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
{"timestamp_utc": "2026-10-07T05:43:54Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T05:45:55Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T05:46:53Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T05:47:10Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T05:47:40Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T05:47:54Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T05:48:57Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T05:51:19Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
```
### recorder.log
```
{"timestamp_utc": "2026-10-07T05:46:07Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: ClientConnectorError: Cannot connect to host api.dexscreener.com:443 ssl:default [Se ha anulado una conexi\u00f3n establecida por el software en su equipo host]"}
{"timestamp_utc": "2026-10-07T05:46:16Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
{"timestamp_utc": "2026-10-07T05:47:09Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T05:48:15Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T05:48:55Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
{"timestamp_utc": "2026-10-07T05:50:03Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T05:50:49Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T05:50:58Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
```

Detalle completo en latest.json.