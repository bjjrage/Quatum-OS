# Snapshot Quant OS — 2026-10-07 10:51 UTC

## Polymarket up/down (paper)

- Señales 298 · llenadas 200 · perdidas 97 (33% se las llevó otro)
- PnL Binance US$ 1445.41 · PnL oficial US$ 0.00 (0 resueltas) · aciertos 0% · t por ventana None
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
- poly_updown: actualizado hace 0.3 min
- pump_azar: actualizado hace 566.9 min
- pump_billeteras: actualizado hace 566.9 min
- pump_billeteras_2x: actualizado hace 566.9 min
- pump_billeteras_azar: actualizado hace 566.9 min
- pump_detector_tarde: actualizado hace 566.9 min
- pump_grupo: actualizado hace 566.9 min
- pump_grupo_aguantar: actualizado hace 566.9 min
- pump_grupo_nicho: actualizado hace 566.9 min
- pump_nicho: actualizado hace 566.9 min
- pump_nicho_azar: actualizado hace 566.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1247 | -0.1 |
| binance_perp/depth_snapshots | 21 | 1.9 |
| binance_perp/forced_liquidations | 60 | 0.3 |
| binance_perp/futures_market_metrics | 60 | 0.3 |
| binance_perp/futures_open_interest | 60 | 0.3 |
| binance_perp/orderbook_l2_depth | 136 | 0.3 |
| binance_perp/trade_ticks | 82 | 0.3 |
| deribit/bbo_ticks | 60 | 0.3 |
| deribit/deribit_metrics | 60 | 0.3 |
| deribit/trade_ticks | 60 | 0.3 |
| dexscreener/token_boosts | 2 | 38.5 |
| dexscreener/token_prices | 9 | 19.0 |
| dexscreener/token_profiles | 5 | 21.6 |
| limitless/limitless_book | 26 | 4.0 |
| limitless/limitless_markets | 11 | 0.2 |
| polymarket/bbo_ticks | 870 | -0.3 |
| polymarket/orderbook_l2_depth | 60 | 0.3 |
| polymarket/polymarket_metadata_history | 16 | 0.3 |
| polymarket/trade_ticks | 60 | 0.3 |
| pumpfun/creator_funding | 16 | 2.6 |
| pumpfun/pumpfun_completes | 13 | 0.1 |
| pumpfun/pumpfun_creates | 44 | 0.1 |
| pumpfun/pumpfun_trades | 46 | 0.1 |
| pumpfun/x_mentions | 0 | 566.9 |
| telegram/calls | 14 | 7.9 |

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
{"timestamp_utc": "2026-10-07T10:35:42Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T10:36:01Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T10:36:06Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T10:47:44Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Binance WS: ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T10:47:57Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Binance WS: TimeoutError: timed out during opening handshake; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T10:48:10Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Binance WS: TimeoutError: timed out during opening handshake; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T10:48:23Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Binance WS: TimeoutError: timed out during opening handshake; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T10:48:29Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: no close frame received or sent; reconecto en 3 s"}
```
### recorder.log
```
{"timestamp_utc": "2026-10-07T10:47:46Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T10:48:20Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T10:48:23Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-07T10:48:37Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T10:50:10Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T10:50:14Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T10:50:47Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T10:50:56Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
```

Detalle completo en latest.json.