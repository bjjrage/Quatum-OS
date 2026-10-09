# Snapshot Quant OS — 2026-10-09 03:51 UTC

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
- poly_updown: actualizado hace 2146.9 min
- pump_azar: actualizado hace 3027.0 min
- pump_billeteras: actualizado hace 3027.0 min
- pump_billeteras_2x: actualizado hace 3027.0 min
- pump_billeteras_azar: actualizado hace 3027.0 min
- pump_detector_tarde: actualizado hace 3027.0 min
- pump_grupo: actualizado hace 3027.0 min
- pump_grupo_aguantar: actualizado hace 3027.0 min
- pump_grupo_nicho: actualizado hace 3027.0 min
- pump_nicho: actualizado hace 3027.0 min
- pump_nicho_azar: actualizado hace 3027.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 914 | -0.4 |
| binance_perp/depth_snapshots | 22 | 0.1 |
| binance_perp/forced_liquidations | 58 | 0.5 |
| binance_perp/futures_market_metrics | 60 | -0.5 |
| binance_perp/futures_open_interest | 61 | -0.5 |
| binance_perp/orderbook_l2_depth | 117 | -0.5 |
| binance_perp/trade_ticks | 66 | -0.5 |
| deribit/bbo_ticks | 61 | -0.5 |
| deribit/deribit_metrics | 61 | -0.5 |
| deribit/trade_ticks | 58 | -0.5 |
| dexscreener/token_boosts | 2 | 6.0 |
| dexscreener/token_prices | 59 | -0.0 |
| dexscreener/token_profiles | 16 | 3.0 |
| limitless/limitless_book | 60 | -0.0 |
| limitless/limitless_markets | 13 | -0.0 |
| polymarket/bbo_ticks | 634 | -0.9 |
| polymarket/orderbook_l2_depth | 61 | -0.5 |
| polymarket/polymarket_metadata_history | 13 | -0.5 |
| polymarket/trade_ticks | 61 | -0.5 |
| pumpfun/creator_funding | 60 | -1.0 |
| pumpfun/pumpfun_completes | 29 | -1.0 |
| pumpfun/pumpfun_creates | 61 | -1.0 |
| pumpfun/pumpfun_trades | 61 | -1.0 |
| pumpfun/x_mentions | 0 | 3027.0 |
| telegram/calls | 9 | 2.0 |

## Problemas en logs (últimos)

### api.log
```
{"timestamp_utc": "2026-10-08T23:58:07Z", "level": "ERROR", "logger": "flujo_paper", "message": "state.json ilegible: NO se sobrescribe; revisar a mano."}
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
{"timestamp_utc": "2026-10-09T03:31:50Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 2s"}
{"timestamp_utc": "2026-10-09T03:31:53Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 4s"}
{"timestamp_utc": "2026-10-09T03:31:58Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 8s"}
{"timestamp_utc": "2026-10-09T03:32:06Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 16s"}
{"timestamp_utc": "2026-10-09T03:32:23Z", "level": "WARNING", "logger": "pumpfun_recorder", "message": "pump.fun WS desconectado (public): InvalidStatus: server rejected WebSocket connection: HTTP 413. Reintento en 32s"}
{"timestamp_utc": "2026-10-09T03:32:45Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T03:40:11Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T03:51:34Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.