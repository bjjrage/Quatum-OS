# Snapshot Quant OS — 2026-10-08 10:51 UTC

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
- poly_updown: actualizado hace 1126.8 min
- pump_azar: actualizado hace 2006.9 min
- pump_billeteras: actualizado hace 2006.9 min
- pump_billeteras_2x: actualizado hace 2006.9 min
- pump_billeteras_azar: actualizado hace 2006.9 min
- pump_detector_tarde: actualizado hace 2006.9 min
- pump_grupo: actualizado hace 2006.9 min
- pump_grupo_aguantar: actualizado hace 2006.9 min
- pump_grupo_nicho: actualizado hace 2006.9 min
- pump_nicho: actualizado hace 2006.9 min
- pump_nicho_azar: actualizado hace 2006.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 159 | -0.1 |
| binance_perp/depth_snapshots | 2 | 0.9 |
| binance_perp/forced_liquidations | 6 | 0.8 |
| binance_perp/futures_market_metrics | 6 | 0.8 |
| binance_perp/futures_open_interest | 7 | -0.2 |
| binance_perp/orderbook_l2_depth | 19 | -0.2 |
| binance_perp/trade_ticks | 9 | -0.2 |
| deribit/bbo_ticks | 7 | -0.2 |
| deribit/deribit_metrics | 7 | -0.2 |
| deribit/trade_ticks | 7 | -0.2 |
| dexscreener/token_boosts | 1 | 5.9 |
| dexscreener/token_prices | 7 | -0.2 |
| dexscreener/token_profiles | 2 | 4.9 |
| limitless/limitless_book | 7 | -0.2 |
| limitless/limitless_markets | 3 | -0.2 |
| polymarket/bbo_ticks | 59 | -0.2 |
| polymarket/orderbook_l2_depth | 7 | -0.2 |
| polymarket/polymarket_metadata_history | 3 | -0.2 |
| polymarket/trade_ticks | 7 | -0.2 |
| pumpfun/creator_funding | 4 | -0.2 |
| pumpfun/pumpfun_completes | 4 | -0.2 |
| pumpfun/pumpfun_creates | 7 | -0.2 |
| pumpfun/pumpfun_trades | 7 | -0.2 |
| pumpfun/x_mentions | 0 | 2006.9 |
| telegram/calls | 3 | -0.2 |

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
{"timestamp_utc": "2026-10-08T00:06:00Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 5.1s..."}
{"timestamp_utc": "2026-10-08T00:06:07Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 7.6s..."}
{"timestamp_utc": "2026-10-08T00:06:46Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T00:06:49Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-08T00:07:44Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T00:07:48Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-08T00:08:05Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-08T10:45:03Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.