# Snapshot Quant OS — 2026-10-09 17:51 UTC

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
- poly_updown: actualizado hace 2986.8 min
- pump_azar: actualizado hace 3866.9 min
- pump_billeteras: actualizado hace 3867.0 min
- pump_billeteras_2x: actualizado hace 3867.0 min
- pump_billeteras_azar: actualizado hace 3867.0 min
- pump_detector_tarde: actualizado hace 3866.9 min
- pump_grupo: actualizado hace 3866.9 min
- pump_grupo_aguantar: actualizado hace 3866.9 min
- pump_grupo_nicho: actualizado hace 3866.9 min
- pump_nicho: actualizado hace 3866.9 min
- pump_nicho_azar: actualizado hace 3866.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 884 | -0.1 |
| binance_perp/depth_snapshots | 20 | 2.9 |
| binance_perp/forced_liquidations | 60 | 0.3 |
| binance_perp/futures_market_metrics | 60 | 0.3 |
| binance_perp/futures_open_interest | 60 | 0.3 |
| binance_perp/orderbook_l2_depth | 121 | -0.2 |
| binance_perp/trade_ticks | 62 | 0.3 |
| deribit/bbo_ticks | 60 | 0.3 |
| deribit/deribit_metrics | 60 | 0.3 |
| deribit/trade_ticks | 59 | 0.3 |
| dexscreener/token_boosts | 7 | 9.0 |
| dexscreener/token_prices | 58 | -0.1 |
| dexscreener/token_profiles | 23 | 3.0 |
| limitless/limitless_book | 60 | -0.1 |
| limitless/limitless_markets | 12 | -0.1 |
| polymarket/bbo_ticks | 1119 | -0.4 |
| polymarket/orderbook_l2_depth | 60 | 0.3 |
| polymarket/polymarket_metadata_history | 16 | 0.3 |
| polymarket/trade_ticks | 57 | 0.3 |
| pumpfun/creator_funding | 60 | -0.1 |
| pumpfun/pumpfun_completes | 38 | 0.9 |
| pumpfun/pumpfun_creates | 60 | -0.1 |
| pumpfun/pumpfun_trades | 68 | -0.1 |
| pumpfun/x_mentions | 0 | 3866.9 |
| telegram/calls | 9 | -0.1 |

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
{"timestamp_utc": "2026-10-09T17:28:35Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T17:28:39Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-09T17:32:33Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T17:33:11Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T17:33:31Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T17:34:20Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T17:38:32Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-09T17:46:51Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.