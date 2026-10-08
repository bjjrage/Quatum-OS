# Snapshot Quant OS — 2026-10-08 11:51 UTC

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
- poly_updown: actualizado hace 1186.8 min
- pump_azar: actualizado hace 2066.9 min
- pump_billeteras: actualizado hace 2066.9 min
- pump_billeteras_2x: actualizado hace 2066.9 min
- pump_billeteras_azar: actualizado hace 2066.9 min
- pump_detector_tarde: actualizado hace 2066.9 min
- pump_grupo: actualizado hace 2066.9 min
- pump_grupo_aguantar: actualizado hace 2066.9 min
- pump_grupo_nicho: actualizado hace 2066.9 min
- pump_nicho: actualizado hace 2066.9 min
- pump_nicho_azar: actualizado hace 2066.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1483 | -0.1 |
| binance_perp/depth_snapshots | 19 | 4.3 |
| binance_perp/forced_liquidations | 60 | -0.0 |
| binance_perp/futures_market_metrics | 61 | -0.0 |
| binance_perp/futures_open_interest | 61 | -0.0 |
| binance_perp/orderbook_l2_depth | 155 | -0.0 |
| binance_perp/trade_ticks | 95 | -0.0 |
| deribit/bbo_ticks | 61 | -0.0 |
| deribit/deribit_metrics | 61 | -0.0 |
| deribit/trade_ticks | 61 | -0.0 |
| dexscreener/token_boosts | 3 | 1.2 |
| dexscreener/token_prices | 60 | 0.2 |
| dexscreener/token_profiles | 15 | 0.2 |
| limitless/limitless_book | 61 | 0.2 |
| limitless/limitless_markets | 16 | 0.2 |
| polymarket/bbo_ticks | 344 | -0.3 |
| polymarket/orderbook_l2_depth | 61 | -0.0 |
| polymarket/polymarket_metadata_history | 17 | -0.0 |
| polymarket/trade_ticks | 56 | -0.0 |
| pumpfun/creator_funding | 57 | 0.2 |
| pumpfun/pumpfun_completes | 31 | 1.2 |
| pumpfun/pumpfun_creates | 61 | 0.2 |
| pumpfun/pumpfun_trades | 61 | 0.2 |
| pumpfun/x_mentions | 0 | 2066.9 |
| telegram/calls | 13 | 3.2 |

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
{"timestamp_utc": "2026-10-08T10:56:56Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-08T10:57:14Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-08T10:57:22Z", "level": "WARNING", "logger": "binance_oi_poller", "message": "Recorded stale Open Interest for BTCUSDT due to polling failure."}
{"timestamp_utc": "2026-10-08T10:57:29Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T11:10:34Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T11:25:18Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T11:40:15Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T11:50:16Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.