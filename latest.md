# Snapshot Quant OS — 2026-10-14 08:51 UTC

## Polymarket up/down (paper)

- Señales 425 · llenadas 291 · perdidas 134 (32% se las llevó otro)
- PnL Binance US$ 1817.40 · PnL oficial US$ -84.10 (291 resueltas) · aciertos 40% · t por ventana -0.8387298218090913
- Criterio: todavía no

## Salud

- api: NEVER_STARTED
- web: NEVER_STARTED
- os_launcher: NEVER_STARTED
- supervisor: NEVER_STARTED
- markets_recorder: NEVER_STARTED
- paper_runtime: STOPPED
- pumpfun_recorder: DISABLED
- pumpfun_paper: DISABLED
- leader_paper: STOPPED
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 484.3 min
- btc_tendencia: actualizado hace 484.3 min
- carry_funding: actualizado hace 484.3 min
- combinada: actualizado hace 484.3 min
- examen_2x: actualizado hace 685.3 min
- flujo_7d: actualizado hace 484.3 min
- flujo_reg200: actualizado hace 484.3 min
- flujo_sectorial: actualizado hace 484.3 min
- flujo_v1: actualizado hace 484.3 min
- lider_azar: actualizado hace 484.3 min
- lider_corto: actualizado hace 484.3 min
- lider_sin_x: actualizado hace 484.3 min
- lider_x: actualizado hace 484.3 min
- mezcla_flujo_carry: actualizado hace 484.3 min
- poly_updown: actualizado hace 9646.8 min
- unlock_short_v1: actualizado hace 525.3 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 0 | 483.5 |
| binance_perp/depth_snapshots | 0 | 484.6 |
| binance_perp/forced_liquidations | 0 | 484.0 |
| binance_perp/futures_market_metrics | 0 | 484.0 |
| binance_perp/futures_open_interest | 0 | 484.0 |
| binance_perp/futures_positioning | 0 | 483.6 |
| binance_perp/orderbook_l2_depth | 0 | 484.0 |
| binance_perp/trade_ticks | 0 | 484.0 |
| deribit/bbo_ticks | 0 | 684.7 |
| deribit/deribit_metrics | 0 | 684.7 |
| deribit/trade_ticks | 0 | 685.7 |
| dexscreener/token_boosts | 0 | 691.9 |
| dexscreener/token_prices | 0 | 684.9 |
| dexscreener/token_profiles | 0 | 686.9 |
| limitless/limitless_book | 0 | 684.9 |
| limitless/limitless_markets | 0 | 684.9 |
| polymarket/bbo_ticks | 0 | 684.7 |
| polymarket/orderbook_l2_depth | 0 | 684.7 |
| polymarket/polymarket_metadata_history | 0 | 685.8 |
| polymarket/trade_ticks | 0 | 684.7 |
| pumpfun/creator_funding | 0 | 684.9 |
| pumpfun/pumpfun_completes | 0 | 684.9 |
| pumpfun/pumpfun_creates | 0 | 684.9 |
| pumpfun/pumpfun_trades | 0 | 684.9 |
| pumpfun/x_mentions | 0 | 10526.9 |
| telegram/calls | 0 | 685.9 |

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
{"timestamp_utc": "2026-10-14T00:17:15Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:20:23Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:30:25Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:30:34Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:31:13Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:32:30Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:35:16Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-14T00:37:16Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.