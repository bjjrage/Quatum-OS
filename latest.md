# Snapshot Quant OS — 2026-10-13 15:51 UTC

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

- baja_vol: actualizado hace 1.1 min
- btc_tendencia: actualizado hace 1.1 min
- carry_funding: actualizado hace 1.1 min
- combinada: actualizado hace 1.1 min
- examen_2x: actualizado hace 1.1 min
- flujo_7d: actualizado hace 1.1 min
- flujo_reg200: actualizado hace 1.1 min
- flujo_sectorial: actualizado hace 1.1 min
- flujo_v1: actualizado hace 1.1 min
- lider_azar: actualizado hace 1.1 min
- lider_corto: actualizado hace 1.1 min
- lider_sin_x: actualizado hace 1.1 min
- lider_x: actualizado hace 1.1 min
- mezcla_flujo_carry: actualizado hace 1.1 min
- poly_updown: actualizado hace 8626.8 min
- unlock_short_v1: actualizado hace 17.4 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1746 | -0.9 |
| binance_perp/depth_snapshots | 22 | -0.7 |
| binance_perp/forced_liquidations | 61 | -1.0 |
| binance_perp/futures_market_metrics | 61 | -1.0 |
| binance_perp/futures_open_interest | 61 | -1.0 |
| binance_perp/futures_positioning | 61 | -0.7 |
| binance_perp/orderbook_l2_depth | 176 | -1.0 |
| binance_perp/trade_ticks | 84 | -1.0 |
| deribit/bbo_ticks | 61 | -1.0 |
| deribit/deribit_metrics | 61 | -1.0 |
| deribit/trade_ticks | 58 | -1.0 |
| dexscreener/token_boosts | 1 | 51.9 |
| dexscreener/token_prices | 61 | -1.2 |
| dexscreener/token_profiles | 19 | -0.2 |
| limitless/limitless_book | 62 | -1.2 |
| limitless/limitless_markets | 14 | -0.2 |
| polymarket/bbo_ticks | 1069 | -1.8 |
| polymarket/orderbook_l2_depth | 61 | -1.0 |
| polymarket/polymarket_metadata_history | 14 | 0.0 |
| polymarket/trade_ticks | 51 | -1.0 |
| pumpfun/creator_funding | 62 | -1.2 |
| pumpfun/pumpfun_completes | 48 | -1.2 |
| pumpfun/pumpfun_creates | 62 | -1.2 |
| pumpfun/pumpfun_trades | 71 | -1.2 |
| pumpfun/x_mentions | 0 | 9506.9 |
| telegram/calls | 17 | 1.8 |

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
{"timestamp_utc": "2026-10-13T14:54:46Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T14:54:50Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-13T14:55:00Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T14:55:07Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-13T14:55:21Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-13T15:05:15Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T15:27:19Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T15:50:12Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.