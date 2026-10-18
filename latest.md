# Snapshot Quant OS — 2026-10-18 23:51 UTC

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

- baja_vol: actualizado hace 0.7 min
- btc_tendencia: actualizado hace 0.7 min
- carry_funding: actualizado hace 0.7 min
- combinada: actualizado hace 0.7 min
- examen_2x: actualizado hace 7345.3 min
- flujo_7d: actualizado hace 0.7 min
- flujo_reg200: actualizado hace 0.7 min
- flujo_sectorial: actualizado hace 0.7 min
- flujo_v1: actualizado hace 0.7 min
- lider_azar: actualizado hace 0.7 min
- lider_corto: actualizado hace 0.7 min
- lider_sin_x: actualizado hace 0.7 min
- lider_x: actualizado hace 0.7 min
- mezcla_flujo_carry: actualizado hace 0.7 min
- poly_updown: actualizado hace 16306.9 min
- unlock_short_v1: actualizado hace 44.8 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1373 | -2.7 |
| binance_perp/depth_snapshots | 21 | -1.2 |
| binance_perp/forced_liquidations | 63 | -2.3 |
| binance_perp/futures_market_metrics | 63 | -2.3 |
| binance_perp/futures_open_interest | 64 | -3.3 |
| binance_perp/futures_positioning | 61 | -3.2 |
| binance_perp/orderbook_l2_depth | 149 | -3.7 |
| binance_perp/trade_ticks | 79 | -3.3 |
| deribit/bbo_ticks | 0 | 7344.8 |
| deribit/deribit_metrics | 0 | 7344.8 |
| deribit/trade_ticks | 0 | 7345.8 |
| dexscreener/token_boosts | 0 | 7351.9 |
| dexscreener/token_prices | 0 | 7344.9 |
| dexscreener/token_profiles | 0 | 7346.9 |
| limitless/limitless_book | 0 | 7344.9 |
| limitless/limitless_markets | 0 | 7344.9 |
| polymarket/bbo_ticks | 0 | 7344.8 |
| polymarket/orderbook_l2_depth | 0 | 7344.8 |
| polymarket/polymarket_metadata_history | 0 | 7345.8 |
| polymarket/trade_ticks | 0 | 7344.8 |
| pumpfun/creator_funding | 0 | 7344.9 |
| pumpfun/pumpfun_completes | 0 | 7344.9 |
| pumpfun/pumpfun_creates | 0 | 7344.9 |
| pumpfun/pumpfun_trades | 0 | 7344.9 |
| pumpfun/x_mentions | 0 | 17187.0 |
| telegram/calls | 0 | 7345.9 |

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
{"timestamp_utc": "2026-10-18T01:37:15Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-18T02:54:19Z", "level": "WARNING", "logger": "binance_oi_poller", "message": "Recorded stale Open Interest for BTCUSDT due to polling failure."}
{"timestamp_utc": "2026-10-18T22:55:19Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-18T22:55:23Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
Traceback (most recent call last):
```

Detalle completo en latest.json.