# Snapshot Quant OS — 2026-10-12 21:51 UTC

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

- baja_vol: actualizado hace 0.7 min
- btc_tendencia: actualizado hace 0.7 min
- carry_funding: actualizado hace 0.7 min
- combinada: actualizado hace 0.7 min
- examen_2x: actualizado hace 0.7 min
- flujo_7d: actualizado hace 0.7 min
- flujo_reg200: actualizado hace 0.7 min
- flujo_sectorial: actualizado hace 0.7 min
- flujo_v1: actualizado hace 0.7 min
- lider_azar: actualizado hace 0.7 min
- lider_corto: actualizado hace 0.7 min
- lider_sin_x: actualizado hace 0.7 min
- lider_x: actualizado hace 0.7 min
- mezcla_flujo_carry: actualizado hace 0.7 min
- poly_updown: actualizado hace 7546.8 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 982 | -0.4 |
| binance_perp/depth_snapshots | 20 | 3.8 |
| binance_perp/forced_liquidations | 60 | -0.5 |
| binance_perp/futures_market_metrics | 61 | -0.5 |
| binance_perp/futures_open_interest | 61 | -0.5 |
| binance_perp/futures_positioning | 61 | -0.2 |
| binance_perp/orderbook_l2_depth | 135 | -0.5 |
| binance_perp/trade_ticks | 86 | -0.5 |
| deribit/bbo_ticks | 61 | -0.5 |
| deribit/deribit_metrics | 61 | -0.5 |
| deribit/trade_ticks | 43 | -0.5 |
| dexscreener/token_boosts | 3 | 7.7 |
| dexscreener/token_prices | 60 | -0.3 |
| dexscreener/token_profiles | 24 | -0.3 |
| limitless/limitless_book | 61 | -0.3 |
| limitless/limitless_markets | 13 | -0.3 |
| polymarket/bbo_ticks | 666 | -1.1 |
| polymarket/orderbook_l2_depth | 61 | -0.5 |
| polymarket/polymarket_metadata_history | 17 | -0.5 |
| polymarket/trade_ticks | 54 | -0.5 |
| pumpfun/creator_funding | 61 | -0.3 |
| pumpfun/pumpfun_completes | 35 | -0.3 |
| pumpfun/pumpfun_creates | 61 | -0.3 |
| pumpfun/pumpfun_trades | 64 | -0.3 |
| pumpfun/x_mentions | 0 | 8426.9 |
| telegram/calls | 15 | 7.7 |

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
{"timestamp_utc": "2026-10-12T21:46:11Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T21:46:15Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T21:46:19Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T21:46:23Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T21:47:09Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T21:47:13Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T21:47:21Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T21:47:31Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.