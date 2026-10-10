# Snapshot Quant OS — 2026-10-10 01:51 UTC

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
- poly_updown: actualizado hace 3466.8 min
- pump_azar: actualizado hace 4346.9 min
- pump_billeteras: actualizado hace 4347.0 min
- pump_billeteras_2x: actualizado hace 4347.0 min
- pump_billeteras_azar: actualizado hace 4347.0 min
- pump_detector_tarde: actualizado hace 4346.9 min
- pump_grupo: actualizado hace 4346.9 min
- pump_grupo_aguantar: actualizado hace 4346.9 min
- pump_grupo_nicho: actualizado hace 4346.9 min
- pump_nicho: actualizado hace 4347.0 min
- pump_nicho_azar: actualizado hace 4347.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 665 | -0.2 |
| binance_perp/depth_snapshots | 20 | 0.7 |
| binance_perp/forced_liquidations | 60 | -0.1 |
| binance_perp/futures_market_metrics | 60 | -0.1 |
| binance_perp/futures_open_interest | 60 | -0.1 |
| binance_perp/orderbook_l2_depth | 119 | -0.1 |
| binance_perp/trade_ticks | 62 | -0.1 |
| deribit/bbo_ticks | 60 | -0.1 |
| deribit/deribit_metrics | 60 | -0.1 |
| deribit/trade_ticks | 36 | -0.1 |
| dexscreener/token_boosts | 4 | 26.7 |
| dexscreener/token_prices | 60 | 0.6 |
| dexscreener/token_profiles | 11 | 5.6 |
| limitless/limitless_book | 60 | 0.6 |
| limitless/limitless_markets | 13 | 0.6 |
| polymarket/bbo_ticks | 1496 | -0.4 |
| polymarket/orderbook_l2_depth | 60 | -0.1 |
| polymarket/polymarket_metadata_history | 16 | -0.1 |
| polymarket/trade_ticks | 60 | -0.1 |
| pumpfun/creator_funding | 61 | -0.4 |
| pumpfun/pumpfun_completes | 38 | -0.4 |
| pumpfun/pumpfun_creates | 61 | -0.4 |
| pumpfun/pumpfun_trades | 61 | -0.4 |
| pumpfun/x_mentions | 0 | 4346.9 |
| telegram/calls | 10 | -0.4 |

## Problemas en logs (últimos)

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
{"timestamp_utc": "2026-10-10T01:43:13Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T01:43:24Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-10T01:45:04Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T01:46:05Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T01:46:23Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T01:47:07Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T01:48:06Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T01:48:23Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.