# Snapshot Quant OS — 2026-10-11 14:51 UTC

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

- baja_vol: actualizado hace 0.1 min
- btc_tendencia: actualizado hace 0.1 min
- carry_funding: actualizado hace 0.1 min
- combinada: actualizado hace 0.1 min
- examen_2x: actualizado hace 0.1 min
- flujo_7d: actualizado hace 0.1 min
- flujo_reg200: actualizado hace 0.1 min
- flujo_v1: actualizado hace 0.1 min
- lider_azar: actualizado hace 0.1 min
- lider_corto: actualizado hace 0.1 min
- lider_sin_x: actualizado hace 0.1 min
- lider_x: actualizado hace 0.1 min
- mezcla_flujo_carry: actualizado hace 0.1 min
- poly_updown: actualizado hace 5686.9 min
- pump_azar: actualizado hace 6567.0 min
- pump_billeteras: actualizado hace 6567.0 min
- pump_billeteras_2x: actualizado hace 6567.0 min
- pump_billeteras_azar: actualizado hace 6567.0 min
- pump_detector_tarde: actualizado hace 6567.0 min
- pump_grupo: actualizado hace 6567.0 min
- pump_grupo_aguantar: actualizado hace 6567.0 min
- pump_grupo_nicho: actualizado hace 6567.0 min
- pump_nicho: actualizado hace 6567.0 min
- pump_nicho_azar: actualizado hace 6567.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 607 | -1.5 |
| binance_perp/depth_snapshots | 21 | 2.3 |
| binance_perp/forced_liquidations | 60 | -1.4 |
| binance_perp/futures_market_metrics | 61 | -1.4 |
| binance_perp/futures_open_interest | 61 | -1.4 |
| binance_perp/futures_positioning | 62 | -1.7 |
| binance_perp/orderbook_l2_depth | 123 | -2.0 |
| binance_perp/trade_ticks | 65 | -1.4 |
| deribit/bbo_ticks | 61 | -1.4 |
| deribit/deribit_metrics | 62 | -2.4 |
| deribit/trade_ticks | 49 | -2.4 |
| dexscreener/token_boosts | 5 | -0.0 |
| dexscreener/token_prices | 63 | -3.0 |
| dexscreener/token_profiles | 27 | -2.0 |
| limitless/limitless_book | 63 | -3.0 |
| limitless/limitless_markets | 12 | -0.0 |
| polymarket/bbo_ticks | 620 | -4.6 |
| polymarket/orderbook_l2_depth | 64 | -4.4 |
| polymarket/polymarket_metadata_history | 19 | -4.4 |
| polymarket/trade_ticks | 62 | -4.4 |
| pumpfun/creator_funding | 64 | -5.0 |
| pumpfun/pumpfun_completes | 38 | -5.0 |
| pumpfun/pumpfun_creates | 65 | -5.0 |
| pumpfun/pumpfun_trades | 66 | -5.0 |
| pumpfun/x_mentions | 0 | 6567.0 |
| telegram/calls | 16 | -5.0 |

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
{"timestamp_utc": "2026-10-11T14:53:14Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T14:54:11Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T14:54:14Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T14:54:15Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-11T14:54:32Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-11T14:54:54Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
{"timestamp_utc": "2026-10-11T14:55:16Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 3.4s..."}
{"timestamp_utc": "2026-10-11T14:55:40Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 5.1s..."}
```

Detalle completo en latest.json.