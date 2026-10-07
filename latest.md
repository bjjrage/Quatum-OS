# Snapshot Quant OS — 2026-10-07 14:51 UTC

## Polymarket up/down (paper)

- Señales 407 · llenadas 279 · perdidas 128 (31% se las llevó otro)
- PnL Binance US$ 1780.66 · PnL oficial US$ 0.00 (0 resueltas) · aciertos 0% · t por ventana None
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
- poly_updown: actualizado hace 0.3 min
- pump_azar: actualizado hace 806.9 min
- pump_billeteras: actualizado hace 806.9 min
- pump_billeteras_2x: actualizado hace 806.9 min
- pump_billeteras_azar: actualizado hace 806.9 min
- pump_detector_tarde: actualizado hace 806.9 min
- pump_grupo: actualizado hace 806.9 min
- pump_grupo_aguantar: actualizado hace 806.9 min
- pump_grupo_nicho: actualizado hace 806.9 min
- pump_nicho: actualizado hace 806.9 min
- pump_nicho_azar: actualizado hace 806.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 986 | -0.1 |
| binance_perp/depth_snapshots | 19 | 2.8 |
| binance_perp/forced_liquidations | 59 | 0.8 |
| binance_perp/futures_market_metrics | 59 | 0.8 |
| binance_perp/futures_open_interest | 59 | 0.8 |
| binance_perp/orderbook_l2_depth | 110 | 0.3 |
| binance_perp/trade_ticks | 95 | 0.8 |
| deribit/bbo_ticks | 60 | -0.2 |
| deribit/deribit_metrics | 63 | -0.2 |
| deribit/trade_ticks | 60 | -0.2 |
| dexscreener/token_boosts | 4 | 0.8 |
| dexscreener/token_prices | 24 | 0.7 |
| dexscreener/token_profiles | 13 | 0.7 |
| limitless/limitless_book | 30 | 2.1 |
| limitless/limitless_markets | 11 | 5.1 |
| polymarket/bbo_ticks | 384 | -0.3 |
| polymarket/orderbook_l2_depth | 60 | -0.2 |
| polymarket/polymarket_metadata_history | 17 | -0.2 |
| polymarket/trade_ticks | 41 | -0.2 |
| pumpfun/creator_funding | 18 | 2.0 |
| pumpfun/pumpfun_completes | 10 | 3.5 |
| pumpfun/pumpfun_creates | 41 | 0.5 |
| pumpfun/pumpfun_trades | 43 | 0.6 |
| pumpfun/x_mentions | 0 | 806.9 |
| telegram/calls | 21 | 1.9 |

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
{"timestamp_utc": "2026-10-07T14:47:31Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T14:47:44Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: TimeoutError: timed out during opening handshake; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T14:48:21Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T14:48:28Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T14:48:41Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: TimeoutError: timed out during opening handshake; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T14:48:59Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T14:49:06Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T14:50:28Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
```
### recorder.log
```
{"timestamp_utc": "2026-10-07T14:49:10Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T14:49:38Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
{"timestamp_utc": "2026-10-07T14:49:39Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T14:50:00Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener respondi\u00f3 404 en dexscreener.com"}
{"timestamp_utc": "2026-10-07T14:50:17Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T14:50:50Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T14:51:18Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
{"timestamp_utc": "2026-10-07T14:51:19Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
```

Detalle completo en latest.json.