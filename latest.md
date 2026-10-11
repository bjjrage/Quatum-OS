# Snapshot Quant OS — 2026-10-11 18:51 UTC

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

- baja_vol: actualizado hace 1.4 min
- btc_tendencia: actualizado hace 1.4 min
- carry_funding: actualizado hace 1.4 min
- combinada: actualizado hace 1.4 min
- examen_2x: actualizado hace 1.4 min
- flujo_7d: actualizado hace 1.4 min
- flujo_reg200: actualizado hace 1.4 min
- flujo_v1: actualizado hace 1.4 min
- lider_azar: actualizado hace 1.4 min
- lider_corto: actualizado hace 1.4 min
- lider_sin_x: actualizado hace 1.4 min
- lider_x: actualizado hace 1.4 min
- mezcla_flujo_carry: actualizado hace 1.4 min
- poly_updown: actualizado hace 5926.9 min
- pump_azar: actualizado hace 6807.0 min
- pump_billeteras: actualizado hace 6807.0 min
- pump_billeteras_2x: actualizado hace 6807.0 min
- pump_billeteras_azar: actualizado hace 6807.0 min
- pump_detector_tarde: actualizado hace 6807.0 min
- pump_grupo: actualizado hace 6807.0 min
- pump_grupo_aguantar: actualizado hace 6807.0 min
- pump_grupo_nicho: actualizado hace 6807.0 min
- pump_nicho: actualizado hace 6807.0 min
- pump_nicho_azar: actualizado hace 6807.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 800 | -0.4 |
| binance_perp/depth_snapshots | 19 | 0.1 |
| binance_perp/forced_liquidations | 61 | -0.4 |
| binance_perp/futures_market_metrics | 61 | -0.4 |
| binance_perp/futures_open_interest | 61 | -0.4 |
| binance_perp/futures_positioning | 60 | 0.1 |
| binance_perp/orderbook_l2_depth | 126 | -0.4 |
| binance_perp/trade_ticks | 69 | -0.4 |
| deribit/bbo_ticks | 61 | -0.4 |
| deribit/deribit_metrics | 61 | -0.4 |
| deribit/trade_ticks | 48 | -0.4 |
| dexscreener/token_boosts | 3 | 16.2 |
| dexscreener/token_prices | 60 | -0.8 |
| dexscreener/token_profiles | 19 | 4.2 |
| limitless/limitless_book | 61 | -0.8 |
| limitless/limitless_markets | 12 | -0.8 |
| polymarket/bbo_ticks | 905 | -1.4 |
| polymarket/orderbook_l2_depth | 61 | -0.4 |
| polymarket/polymarket_metadata_history | 17 | 0.6 |
| polymarket/trade_ticks | 60 | -1.4 |
| pumpfun/creator_funding | 61 | -0.8 |
| pumpfun/pumpfun_completes | 47 | 1.2 |
| pumpfun/pumpfun_creates | 61 | -0.8 |
| pumpfun/pumpfun_trades | 63 | -0.8 |
| pumpfun/x_mentions | 0 | 6807.0 |
| telegram/calls | 15 | 3.2 |

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
{"timestamp_utc": "2026-10-11T18:46:29Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T18:46:50Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T18:47:26Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T18:47:31Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T18:47:36Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T18:47:40Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T18:47:44Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T18:47:51Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.