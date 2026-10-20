# Snapshot Quant OS — 2026-10-20 00:51 UTC

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
- pumpfun_recorder: DISABLED
- pumpfun_paper: DISABLED
- leader_paper: RUNNING
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 0.4 min
- btc_tendencia: actualizado hace 0.4 min
- carry_funding: actualizado hace 0.4 min
- combinada: actualizado hace 0.4 min
- examen_2x: actualizado hace 8845.3 min
- flujo_7d: actualizado hace 0.4 min
- flujo_reg200: actualizado hace 0.4 min
- flujo_sectorial: actualizado hace 0.4 min
- flujo_v1: actualizado hace 0.4 min
- lider_azar: actualizado hace 0.4 min
- lider_corto: actualizado hace 0.4 min
- lider_sin_x: actualizado hace 0.4 min
- lider_x: actualizado hace 0.4 min
- mezcla_flujo_carry: actualizado hace 0.4 min
- poly_updown: actualizado hace 17806.9 min
- unlock_short_v1: actualizado hace 45.4 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1522 | -2.1 |
| binance_perp/depth_snapshots | 22 | -1.4 |
| binance_perp/forced_liquidations | 61 | -2.1 |
| binance_perp/futures_market_metrics | 62 | -2.1 |
| binance_perp/futures_open_interest | 62 | -2.1 |
| binance_perp/futures_positioning | 63 | -2.4 |
| binance_perp/orderbook_l2_depth | 160 | -2.6 |
| binance_perp/trade_ticks | 72 | -2.1 |
| deribit/bbo_ticks | 0 | 8844.7 |
| deribit/deribit_metrics | 0 | 8844.7 |
| deribit/trade_ticks | 0 | 8845.7 |
| dexscreener/token_boosts | 0 | 8851.9 |
| dexscreener/token_prices | 0 | 8844.9 |
| dexscreener/token_profiles | 0 | 8846.9 |
| limitless/limitless_book | 0 | 8844.9 |
| limitless/limitless_markets | 0 | 8844.9 |
| polymarket/bbo_ticks | 0 | 8844.7 |
| polymarket/orderbook_l2_depth | 0 | 8844.7 |
| polymarket/polymarket_metadata_history | 0 | 8845.8 |
| polymarket/trade_ticks | 0 | 8844.7 |
| pumpfun/creator_funding | 0 | 8844.9 |
| pumpfun/pumpfun_completes | 0 | 8844.9 |
| pumpfun/pumpfun_creates | 0 | 8844.9 |
| pumpfun/pumpfun_trades | 0 | 8844.9 |
| pumpfun/x_mentions | 0 | 18687.0 |
| telegram/calls | 0 | 8845.9 |

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
{"timestamp_utc": "2026-10-19T23:54:53Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-19T23:55:21Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-20T00:40:07Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-20T00:54:30Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-20T00:54:35Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-20T00:54:38Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-20T00:54:51Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-20T00:54:56Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
```

Detalle completo en latest.json.