# Snapshot Quant OS — 2026-10-11 17:51 UTC

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

- baja_vol: actualizado hace 0.8 min
- btc_tendencia: actualizado hace 0.8 min
- carry_funding: actualizado hace 0.8 min
- combinada: actualizado hace 0.8 min
- examen_2x: actualizado hace 0.8 min
- flujo_7d: actualizado hace 0.8 min
- flujo_reg200: actualizado hace 0.8 min
- flujo_v1: actualizado hace 0.8 min
- lider_azar: actualizado hace 0.8 min
- lider_corto: actualizado hace 0.8 min
- lider_sin_x: actualizado hace 0.8 min
- lider_x: actualizado hace 0.8 min
- mezcla_flujo_carry: actualizado hace 0.8 min
- poly_updown: actualizado hace 5866.9 min
- pump_azar: actualizado hace 6747.0 min
- pump_billeteras: actualizado hace 6747.0 min
- pump_billeteras_2x: actualizado hace 6747.0 min
- pump_billeteras_azar: actualizado hace 6747.0 min
- pump_detector_tarde: actualizado hace 6747.0 min
- pump_grupo: actualizado hace 6747.0 min
- pump_grupo_aguantar: actualizado hace 6747.0 min
- pump_grupo_nicho: actualizado hace 6747.0 min
- pump_nicho: actualizado hace 6747.0 min
- pump_nicho_azar: actualizado hace 6747.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1044 | -0.6 |
| binance_perp/depth_snapshots | 19 | 0.2 |
| binance_perp/forced_liquidations | 60 | -0.1 |
| binance_perp/futures_market_metrics | 60 | -0.1 |
| binance_perp/futures_open_interest | 60 | -0.1 |
| binance_perp/futures_positioning | 61 | -0.8 |
| binance_perp/orderbook_l2_depth | 127 | -0.7 |
| binance_perp/trade_ticks | 72 | -0.1 |
| deribit/bbo_ticks | 61 | -1.1 |
| deribit/deribit_metrics | 61 | -1.1 |
| deribit/trade_ticks | 55 | -1.1 |
| dexscreener/token_boosts | 4 | 1.3 |
| dexscreener/token_prices | 60 | -0.7 |
| dexscreener/token_profiles | 17 | 1.3 |
| limitless/limitless_book | 61 | -0.7 |
| limitless/limitless_markets | 13 | 0.3 |
| polymarket/bbo_ticks | 628 | -1.1 |
| polymarket/orderbook_l2_depth | 61 | -1.1 |
| polymarket/polymarket_metadata_history | 16 | -0.1 |
| polymarket/trade_ticks | 52 | 2.9 |
| pumpfun/creator_funding | 62 | -1.7 |
| pumpfun/pumpfun_completes | 35 | -0.7 |
| pumpfun/pumpfun_creates | 62 | -1.7 |
| pumpfun/pumpfun_trades | 62 | -1.7 |
| pumpfun/x_mentions | 0 | 6747.0 |
| telegram/calls | 13 | 0.3 |

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
{"timestamp_utc": "2026-10-11T17:02:47Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T17:02:59Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T17:11:45Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T17:16:31Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T17:31:20Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T17:36:07Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T17:36:12Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T17:48:00Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.