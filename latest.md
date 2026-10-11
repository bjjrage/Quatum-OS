# Snapshot Quant OS — 2026-10-11 05:51 UTC

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
- flujo_reg200: actualizado hace 1.6 min
- flujo_v1: actualizado hace 1.6 min
- lider_azar: actualizado hace 1.6 min
- lider_corto: actualizado hace 1.6 min
- lider_sin_x: actualizado hace 1.6 min
- lider_x: actualizado hace 1.6 min
- mezcla_flujo_carry: actualizado hace 1.6 min
- poly_updown: actualizado hace 5147.1 min
- pump_azar: actualizado hace 6027.2 min
- pump_billeteras: actualizado hace 6027.2 min
- pump_billeteras_2x: actualizado hace 6027.2 min
- pump_billeteras_azar: actualizado hace 6027.2 min
- pump_detector_tarde: actualizado hace 6027.2 min
- pump_grupo: actualizado hace 6027.2 min
- pump_grupo_aguantar: actualizado hace 6027.2 min
- pump_grupo_nicho: actualizado hace 6027.2 min
- pump_nicho: actualizado hace 6027.2 min
- pump_nicho_azar: actualizado hace 6027.2 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 535 | -5.3 |
| binance_perp/depth_snapshots | 21 | -5.2 |
| binance_perp/forced_liquidations | 64 | -4.8 |
| binance_perp/futures_market_metrics | 65 | -5.8 |
| binance_perp/futures_open_interest | 66 | -5.8 |
| binance_perp/futures_positioning | 66 | -5.2 |
| binance_perp/orderbook_l2_depth | 129 | -5.8 |
| binance_perp/trade_ticks | 65 | -5.8 |
| deribit/bbo_ticks | 66 | -5.8 |
| deribit/deribit_metrics | 66 | -5.8 |
| deribit/trade_ticks | 44 | -4.8 |
| dexscreener/token_boosts | 4 | 20.5 |
| dexscreener/token_prices | 66 | -5.6 |
| dexscreener/token_profiles | 12 | -3.6 |
| limitless/limitless_book | 67 | -6.6 |
| limitless/limitless_markets | 14 | -5.6 |
| polymarket/bbo_ticks | 1089 | -7.0 |
| polymarket/orderbook_l2_depth | 67 | -6.8 |
| polymarket/polymarket_metadata_history | 18 | -4.8 |
| polymarket/trade_ticks | 64 | -6.8 |
| pumpfun/creator_funding | 62 | -6.6 |
| pumpfun/pumpfun_completes | 29 | -6.6 |
| pumpfun/pumpfun_creates | 67 | -6.6 |
| pumpfun/pumpfun_trades | 67 | -6.6 |
| pumpfun/x_mentions | 0 | 6027.2 |
| telegram/calls | 8 | 5.4 |

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
{"timestamp_utc": "2026-10-11T05:44:16Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T05:54:09Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T05:54:09Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T05:54:12Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-11T05:54:30Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-11T05:54:30Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-11T05:54:51Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
{"timestamp_utc": "2026-10-11T05:54:51Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
```

Detalle completo en latest.json.