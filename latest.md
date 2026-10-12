# Snapshot Quant OS — 2026-10-12 12:51 UTC

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
- flujo_v1: actualizado hace 1.1 min
- lider_azar: actualizado hace 1.1 min
- lider_corto: actualizado hace 1.1 min
- lider_sin_x: actualizado hace 1.1 min
- lider_x: actualizado hace 1.1 min
- mezcla_flujo_carry: actualizado hace 1.1 min
- poly_updown: actualizado hace 7006.8 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1457 | -0.2 |
| binance_perp/depth_snapshots | 20 | -0.2 |
| binance_perp/forced_liquidations | 60 | 0.6 |
| binance_perp/futures_market_metrics | 60 | 0.6 |
| binance_perp/futures_open_interest | 60 | 0.6 |
| binance_perp/futures_positioning | 60 | -0.2 |
| binance_perp/orderbook_l2_depth | 140 | 0.0 |
| binance_perp/trade_ticks | 86 | 0.6 |
| deribit/bbo_ticks | 60 | 0.6 |
| deribit/deribit_metrics | 60 | 0.6 |
| deribit/trade_ticks | 60 | 0.6 |
| dexscreener/token_boosts | 7 | 15.2 |
| dexscreener/token_prices | 60 | 0.2 |
| dexscreener/token_profiles | 21 | 0.2 |
| limitless/limitless_book | 60 | 0.2 |
| limitless/limitless_markets | 12 | 0.2 |
| polymarket/bbo_ticks | 584 | -0.4 |
| polymarket/orderbook_l2_depth | 61 | -0.4 |
| polymarket/polymarket_metadata_history | 17 | -0.4 |
| polymarket/trade_ticks | 58 | -0.4 |
| pumpfun/creator_funding | 60 | 0.2 |
| pumpfun/pumpfun_completes | 25 | 2.2 |
| pumpfun/pumpfun_creates | 60 | 0.2 |
| pumpfun/pumpfun_trades | 60 | 0.2 |
| pumpfun/x_mentions | 0 | 7886.9 |
| telegram/calls | 10 | 20.2 |

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
{"timestamp_utc": "2026-10-12T12:35:25Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T12:35:35Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T12:36:45Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T12:36:49Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T12:37:32Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T12:37:37Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T12:37:48Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T12:45:56Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.