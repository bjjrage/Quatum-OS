# Snapshot Quant OS — 2026-10-20 02:51 UTC

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

- baja_vol: actualizado hace 1.4 min
- btc_tendencia: actualizado hace 1.4 min
- carry_funding: actualizado hace 1.4 min
- combinada: actualizado hace 1.4 min
- examen_2x: actualizado hace 8965.3 min
- flujo_7d: actualizado hace 1.4 min
- flujo_reg200: actualizado hace 1.4 min
- flujo_sectorial: actualizado hace 1.4 min
- flujo_v1: actualizado hace 1.4 min
- lider_azar: actualizado hace 1.4 min
- lider_corto: actualizado hace 1.4 min
- lider_sin_x: actualizado hace 1.4 min
- lider_x: actualizado hace 1.4 min
- mezcla_flujo_carry: actualizado hace 1.4 min
- poly_updown: actualizado hace 17926.9 min
- unlock_short_v1: actualizado hace 45.5 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1424 | -2.4 |
| binance_perp/depth_snapshots | 21 | -0.4 |
| binance_perp/forced_liquidations | 61 | -2.4 |
| binance_perp/futures_market_metrics | 64 | -3.4 |
| binance_perp/futures_open_interest | 64 | -3.4 |
| binance_perp/futures_positioning | 63 | -2.4 |
| binance_perp/orderbook_l2_depth | 158 | -4.4 |
| binance_perp/trade_ticks | 69 | -4.4 |
| deribit/bbo_ticks | 0 | 8964.8 |
| deribit/deribit_metrics | 0 | 8964.8 |
| deribit/trade_ticks | 0 | 8965.8 |
| dexscreener/token_boosts | 0 | 8972.0 |
| dexscreener/token_prices | 0 | 8964.9 |
| dexscreener/token_profiles | 0 | 8966.9 |
| limitless/limitless_book | 0 | 8964.9 |
| limitless/limitless_markets | 0 | 8964.9 |
| polymarket/bbo_ticks | 0 | 8964.8 |
| polymarket/orderbook_l2_depth | 0 | 8964.8 |
| polymarket/polymarket_metadata_history | 0 | 8965.8 |
| polymarket/trade_ticks | 0 | 8964.8 |
| pumpfun/creator_funding | 0 | 8964.9 |
| pumpfun/pumpfun_completes | 0 | 8964.9 |
| pumpfun/pumpfun_creates | 0 | 8964.9 |
| pumpfun/pumpfun_trades | 0 | 8964.9 |
| pumpfun/x_mentions | 0 | 18807.0 |
| telegram/calls | 0 | 8965.9 |

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
{"timestamp_utc": "2026-10-20T02:54:07Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-20T02:54:28Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-20T02:54:47Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-20T02:54:50Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
{"timestamp_utc": "2026-10-20T02:54:51Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-20T02:55:08Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-20T02:55:12Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 3.4s..."}
Traceback (most recent call last):
```

Detalle completo en latest.json.