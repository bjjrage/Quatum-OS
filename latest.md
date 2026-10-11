# Snapshot Quant OS — 2026-10-11 19:51 UTC

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

- baja_vol: actualizado hace 1.7 min
- btc_tendencia: actualizado hace 1.7 min
- carry_funding: actualizado hace 1.7 min
- combinada: actualizado hace 1.7 min
- examen_2x: actualizado hace 1.7 min
- flujo_7d: actualizado hace 1.7 min
- flujo_reg200: actualizado hace 1.7 min
- flujo_v1: actualizado hace 1.7 min
- lider_azar: actualizado hace 1.7 min
- lider_corto: actualizado hace 1.7 min
- lider_sin_x: actualizado hace 1.7 min
- lider_x: actualizado hace 1.7 min
- mezcla_flujo_carry: actualizado hace 1.7 min
- poly_updown: actualizado hace 5986.9 min
- pump_azar: actualizado hace 6867.0 min
- pump_billeteras: actualizado hace 6867.0 min
- pump_billeteras_2x: actualizado hace 6867.0 min
- pump_billeteras_azar: actualizado hace 6867.0 min
- pump_detector_tarde: actualizado hace 6867.0 min
- pump_grupo: actualizado hace 6867.0 min
- pump_grupo_aguantar: actualizado hace 6867.0 min
- pump_grupo_nicho: actualizado hace 6867.0 min
- pump_nicho: actualizado hace 6867.0 min
- pump_nicho_azar: actualizado hace 6867.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 628 | -1.4 |
| binance_perp/depth_snapshots | 20 | 0.1 |
| binance_perp/forced_liquidations | 61 | -1.8 |
| binance_perp/futures_market_metrics | 62 | -1.8 |
| binance_perp/futures_open_interest | 62 | -1.8 |
| binance_perp/futures_positioning | 62 | -1.9 |
| binance_perp/orderbook_l2_depth | 123 | -2.4 |
| binance_perp/trade_ticks | 62 | -1.8 |
| deribit/bbo_ticks | 63 | -2.8 |
| deribit/deribit_metrics | 63 | -2.8 |
| deribit/trade_ticks | 37 | -2.8 |
| dexscreener/token_boosts | 5 | 4.1 |
| dexscreener/token_prices | 62 | -2.0 |
| dexscreener/token_profiles | 20 | 0.0 |
| limitless/limitless_book | 63 | -3.0 |
| limitless/limitless_markets | 13 | 0.0 |
| polymarket/bbo_ticks | 516 | -3.5 |
| polymarket/orderbook_l2_depth | 64 | -3.8 |
| polymarket/polymarket_metadata_history | 12 | 0.3 |
| polymarket/trade_ticks | 59 | -3.8 |
| pumpfun/creator_funding | 64 | -4.0 |
| pumpfun/pumpfun_completes | 38 | -3.0 |
| pumpfun/pumpfun_creates | 64 | -4.0 |
| pumpfun/pumpfun_trades | 64 | -4.0 |
| pumpfun/x_mentions | 0 | 6867.0 |
| telegram/calls | 14 | 2.0 |

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
{"timestamp_utc": "2026-10-11T19:35:31Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T19:36:11Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T19:54:21Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T19:54:24Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-11T19:54:29Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T19:54:42Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-11T19:54:50Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-11T19:55:03Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
```

Detalle completo en latest.json.