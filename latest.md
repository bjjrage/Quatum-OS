# Snapshot Quant OS — 2026-10-12 01:51 UTC

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
- poly_updown: actualizado hace 6348.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1095 | -2.8 |
| binance_perp/depth_snapshots | 22 | -1.6 |
| binance_perp/forced_liquidations | 68 | -9.9 |
| binance_perp/futures_market_metrics | 71 | -13.0 |
| binance_perp/futures_open_interest | 75 | -16.0 |
| binance_perp/futures_positioning | 75 | -15.6 |
| binance_perp/orderbook_l2_depth | 160 | -17.5 |
| binance_perp/trade_ticks | 84 | -18.0 |
| deribit/bbo_ticks | 77 | -18.0 |
| deribit/deribit_metrics | 78 | -19.0 |
| deribit/trade_ticks | 70 | -19.0 |
| dexscreener/token_boosts | 6 | 14.0 |
| dexscreener/token_prices | 75 | -18.7 |
| dexscreener/token_profiles | 14 | -17.7 |
| limitless/limitless_book | 78 | -18.7 |
| limitless/limitless_markets | 16 | -18.7 |
| polymarket/bbo_ticks | 1192 | -25.1 |
| polymarket/orderbook_l2_depth | 84 | -25.1 |
| polymarket/polymarket_metadata_history | 19 | -23.1 |
| polymarket/trade_ticks | 82 | -27.1 |
| pumpfun/creator_funding | 85 | -26.7 |
| pumpfun/pumpfun_completes | 46 | -27.8 |
| pumpfun/pumpfun_creates | 96 | -36.8 |
| pumpfun/pumpfun_trades | 99 | -38.8 |
| pumpfun/x_mentions | 0 | 7228.1 |
| telegram/calls | 15 | -31.8 |

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
{"timestamp_utc": "2026-10-12T02:04:22Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T02:07:30Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T02:13:20Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T02:18:26Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T02:18:30Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T02:18:35Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T02:19:59Z", "level": "WARNING", "logger": "flujo_paper", "message": "Paper: PermissionError: [WinError 5] Acceso denegado: 'C:\\\\Users\\\\User\\\\Desktop\\\\PORYECTOS\\\\TRADING OS\\\\data\\\\paper\\\\mezcla_flujo_carry\\\\state.tmp' -> 'C:\\\\Users\\\\User\\\\Deskt"}
{"timestamp_utc": "2026-10-12T02:26:53Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.