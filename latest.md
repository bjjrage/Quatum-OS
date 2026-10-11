# Snapshot Quant OS — 2026-10-11 02:51 UTC

## Polymarket up/down (paper)

- Señales 425 · llenadas 291 · perdidas 134 (32% se las llevó otro)
- PnL Binance US$ 1817.40 · PnL oficial US$ -84.10 (291 resueltas) · aciertos 40% · t por ventana -0.8387298218090913
- Criterio: todavía no

## Salud

- api: STOPPED
- web: STOPPED
- os_launcher: STOPPED
- supervisor: STOPPED
- markets_recorder: STOPPED
- paper_runtime: ERROR
- pumpfun_recorder: STOPPED
- pumpfun_paper: DISABLED
- leader_paper: STOPPED
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 11.6 min
- btc_tendencia: actualizado hace 11.6 min
- carry_funding: actualizado hace 11.6 min
- combinada: actualizado hace 11.6 min
- examen_2x: actualizado hace 11.6 min
- flujo_7d: actualizado hace 11.6 min
- flujo_reg200: actualizado hace 11.6 min
- flujo_v1: actualizado hace 11.6 min
- lider_azar: actualizado hace 11.6 min
- lider_corto: actualizado hace 11.6 min
- lider_sin_x: actualizado hace 11.6 min
- lider_x: actualizado hace 11.6 min
- mezcla_flujo_carry: actualizado hace 11.6 min
- poly_updown: actualizado hace 4966.9 min
- pump_azar: actualizado hace 5847.0 min
- pump_billeteras: actualizado hace 5847.0 min
- pump_billeteras_2x: actualizado hace 5847.0 min
- pump_billeteras_azar: actualizado hace 5847.0 min
- pump_detector_tarde: actualizado hace 5847.0 min
- pump_grupo: actualizado hace 5847.0 min
- pump_grupo_aguantar: actualizado hace 5847.0 min
- pump_grupo_nicho: actualizado hace 5847.0 min
- pump_nicho: actualizado hace 5847.0 min
- pump_nicho_azar: actualizado hace 5847.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 402 | 11.4 |
| binance_perp/depth_snapshots | 15 | 16.7 |
| binance_perp/forced_liquidations | 48 | 12.1 |
| binance_perp/futures_market_metrics | 48 | 12.1 |
| binance_perp/futures_open_interest | 48 | 12.1 |
| binance_perp/futures_positioning | 49 | 11.7 |
| binance_perp/orderbook_l2_depth | 97 | 11.5 |
| binance_perp/trade_ticks | 49 | 12.1 |
| deribit/bbo_ticks | 48 | 12.1 |
| deribit/deribit_metrics | 48 | 12.1 |
| deribit/trade_ticks | 29 | 13.1 |
| dexscreener/token_boosts | 1 | 45.5 |
| dexscreener/token_prices | 49 | 11.3 |
| dexscreener/token_profiles | 14 | 13.3 |
| limitless/limitless_book | 49 | 11.3 |
| limitless/limitless_markets | 11 | 15.3 |
| polymarket/bbo_ticks | 461 | -1.9 |
| polymarket/orderbook_l2_depth | 48 | 12.1 |
| polymarket/polymarket_metadata_history | 10 | 15.1 |
| polymarket/trade_ticks | 41 | 12.1 |
| pumpfun/creator_funding | 49 | 11.3 |
| pumpfun/pumpfun_completes | 19 | 16.3 |
| pumpfun/pumpfun_creates | 49 | 11.3 |
| pumpfun/pumpfun_trades | 50 | -2.3 |
| pumpfun/x_mentions | 0 | 5847.0 |
| telegram/calls | 8 | 18.4 |

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
{"timestamp_utc": "2026-10-11T01:54:17Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-11T01:54:18Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T01:54:35Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-11T01:54:39Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-11T01:55:06Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T02:00:15Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T02:26:25Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-11T02:52:27Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
```

Detalle completo en latest.json.