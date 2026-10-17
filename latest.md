# Snapshot Quant OS — 2026-10-17 02:53 UTC

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

- baja_vol: actualizado hace 0.8 min
- btc_tendencia: actualizado hace 0.8 min
- carry_funding: actualizado hace 0.8 min
- combinada: actualizado hace 0.8 min
- examen_2x: actualizado hace 4650.7 min
- flujo_7d: actualizado hace 0.8 min
- flujo_reg200: actualizado hace 0.8 min
- flujo_sectorial: actualizado hace 0.8 min
- flujo_v1: actualizado hace 0.8 min
- lider_azar: actualizado hace 0.8 min
- lider_corto: actualizado hace 0.8 min
- lider_sin_x: actualizado hace 0.8 min
- lider_x: actualizado hace 0.8 min
- mezcla_flujo_carry: actualizado hace 0.8 min
- poly_updown: actualizado hace 13612.3 min
- unlock_short_v1: actualizado hace 50.5 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 951 | -24.6 |
| binance_perp/depth_snapshots | 30 | -23.8 |
| binance_perp/forced_liquidations | 83 | -24.3 |
| binance_perp/futures_market_metrics | 84 | -24.3 |
| binance_perp/futures_open_interest | 84 | -24.3 |
| binance_perp/futures_positioning | 85 | -24.8 |
| binance_perp/orderbook_l2_depth | 174 | -25.3 |
| binance_perp/trade_ticks | 89 | -26.3 |
| deribit/bbo_ticks | 0 | 4650.3 |
| deribit/deribit_metrics | 0 | 4650.3 |
| deribit/trade_ticks | 0 | 4651.3 |
| dexscreener/token_boosts | 0 | 4657.4 |
| dexscreener/token_prices | 0 | 4650.4 |
| dexscreener/token_profiles | 0 | 4652.4 |
| limitless/limitless_book | 0 | 4650.4 |
| limitless/limitless_markets | 0 | 4650.4 |
| polymarket/bbo_ticks | 0 | 4650.3 |
| polymarket/orderbook_l2_depth | 0 | 4650.3 |
| polymarket/polymarket_metadata_history | 0 | 4651.3 |
| polymarket/trade_ticks | 0 | 4650.3 |
| pumpfun/creator_funding | 0 | 4650.4 |
| pumpfun/pumpfun_completes | 0 | 4650.4 |
| pumpfun/pumpfun_creates | 0 | 4650.4 |
| pumpfun/pumpfun_trades | 0 | 4650.4 |
| pumpfun/x_mentions | 0 | 14492.5 |
| telegram/calls | 0 | 4651.4 |

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
{"timestamp_utc": "2026-10-17T01:55:17Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-17T02:54:24Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-17T02:54:28Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-17T02:54:31Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-17T02:54:45Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-17T02:54:52Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-17T02:55:07Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
{"timestamp_utc": "2026-10-17T02:55:13Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
```

Detalle completo en latest.json.