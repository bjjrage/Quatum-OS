# Snapshot Quant OS — 2026-10-07 07:51 UTC

## Polymarket up/down (paper)

- Señales 184 · llenadas 125 · perdidas 56 (30% se las llevó otro)
- PnL Binance US$ 659.49 · PnL oficial US$ 0.00 (0 resueltas) · aciertos 0% · t por ventana None
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

- baja_vol: actualizado hace 0.3 min
- btc_tendencia: actualizado hace 0.3 min
- carry_funding: actualizado hace 0.3 min
- combinada: actualizado hace 0.3 min
- examen_2x: actualizado hace 0.3 min
- flujo_7d: actualizado hace 0.3 min
- flujo_v1: actualizado hace 0.3 min
- lider_azar: actualizado hace 0.3 min
- lider_corto: actualizado hace 0.3 min
- lider_sin_x: actualizado hace 0.3 min
- lider_x: actualizado hace 0.3 min
- poly_updown: actualizado hace 0.5 min
- pump_azar: actualizado hace 386.9 min
- pump_billeteras: actualizado hace 386.9 min
- pump_billeteras_2x: actualizado hace 386.9 min
- pump_billeteras_azar: actualizado hace 386.9 min
- pump_detector_tarde: actualizado hace 386.9 min
- pump_grupo: actualizado hace 386.9 min
- pump_grupo_aguantar: actualizado hace 386.9 min
- pump_grupo_nicho: actualizado hace 386.9 min
- pump_nicho: actualizado hace 386.9 min
- pump_nicho_azar: actualizado hace 386.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 798 | -0.0 |
| binance_perp/depth_snapshots | 18 | 4.9 |
| binance_perp/forced_liquidations | 60 | 0.3 |
| binance_perp/futures_market_metrics | 60 | 0.3 |
| binance_perp/futures_open_interest | 60 | 0.3 |
| binance_perp/orderbook_l2_depth | 121 | 0.3 |
| binance_perp/trade_ticks | 60 | 0.3 |
| deribit/bbo_ticks | 60 | 0.3 |
| deribit/deribit_metrics | 60 | 0.3 |
| deribit/trade_ticks | 58 | 0.3 |
| dexscreener/token_boosts | 2 | 27.8 |
| dexscreener/token_prices | 12 | 6.7 |
| dexscreener/token_profiles | 7 | 6.7 |
| limitless/limitless_book | 32 | 1.3 |
| limitless/limitless_markets | 11 | 0.1 |
| polymarket/bbo_ticks | 437 | 0.3 |
| polymarket/orderbook_l2_depth | 60 | 0.3 |
| polymarket/polymarket_metadata_history | 16 | 0.3 |
| polymarket/trade_ticks | 49 | 0.3 |
| pumpfun/creator_funding | 28 | -0.1 |
| pumpfun/pumpfun_completes | 19 | 1.3 |
| pumpfun/pumpfun_creates | 46 | -0.0 |
| pumpfun/pumpfun_trades | 46 | 0.1 |
| pumpfun/x_mentions | 0 | 386.9 |
| telegram/calls | 5 | 13.1 |

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
{"timestamp_utc": "2026-10-07T07:45:46Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T07:46:01Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T07:47:12Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T07:47:17Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T07:47:39Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T07:50:24Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T07:50:32Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
{"timestamp_utc": "2026-10-07T07:50:37Z", "level": "WARNING", "logger": "poly_updown_paper", "message": "Polymarket WS: ConnectionClosedError: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send bu; reconecto en 3 s"}
```
### recorder.log
```
{"timestamp_utc": "2026-10-07T07:48:53Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T07:48:54Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T07:49:29Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T07:49:52Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
{"timestamp_utc": "2026-10-07T07:50:02Z", "level": "WARNING", "logger": "limitless_recorder", "message": "Limitless: TimeoutError: "}
{"timestamp_utc": "2026-10-07T07:50:19Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reintento en 1s"}
{"timestamp_utc": "2026-10-07T07:50:25Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-07T07:50:44Z", "level": "WARNING", "logger": "dexscreener_watcher", "message": "DexScreener: TimeoutError: "}
```

Detalle completo en latest.json.