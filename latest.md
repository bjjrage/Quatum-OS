# Snapshot Quant OS — 2026-10-12 23:51 UTC

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

- baja_vol: actualizado hace 1.8 min
- btc_tendencia: actualizado hace 1.8 min
- carry_funding: actualizado hace 1.8 min
- combinada: actualizado hace 1.8 min
- examen_2x: actualizado hace 1.8 min
- flujo_7d: actualizado hace 1.8 min
- flujo_reg200: actualizado hace 1.8 min
- flujo_sectorial: actualizado hace 1.8 min
- flujo_v1: actualizado hace 1.8 min
- lider_azar: actualizado hace 1.8 min
- lider_corto: actualizado hace 1.8 min
- lider_sin_x: actualizado hace 1.8 min
- lider_x: actualizado hace 1.8 min
- mezcla_flujo_carry: actualizado hace 1.8 min
- poly_updown: actualizado hace 7666.9 min
- unlock_short_v1: actualizado hace 0.1 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1741 | -1.0 |
| binance_perp/depth_snapshots | 19 | 0.8 |
| binance_perp/forced_liquidations | 61 | -0.6 |
| binance_perp/futures_market_metrics | 61 | -0.6 |
| binance_perp/futures_open_interest | 61 | -0.6 |
| binance_perp/futures_positioning | 62 | -1.2 |
| binance_perp/orderbook_l2_depth | 151 | -1.3 |
| binance_perp/trade_ticks | 131 | -0.6 |
| deribit/bbo_ticks | 61 | -0.6 |
| deribit/deribit_metrics | 62 | -0.6 |
| deribit/trade_ticks | 56 | -0.6 |
| dexscreener/token_boosts | 5 | 4.4 |
| dexscreener/token_prices | 59 | -0.6 |
| dexscreener/token_profiles | 11 | 2.4 |
| limitless/limitless_book | 62 | -1.6 |
| limitless/limitless_markets | 13 | 0.4 |
| polymarket/bbo_ticks | 830 | -2.2 |
| polymarket/orderbook_l2_depth | 62 | -1.6 |
| polymarket/polymarket_metadata_history | 17 | -0.6 |
| polymarket/trade_ticks | 61 | -1.6 |
| pumpfun/creator_funding | 62 | -1.6 |
| pumpfun/pumpfun_completes | 34 | 0.4 |
| pumpfun/pumpfun_creates | 62 | -1.6 |
| pumpfun/pumpfun_trades | 62 | -1.6 |
| pumpfun/x_mentions | 0 | 8547.0 |
| telegram/calls | 10 | 0.4 |

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
{"timestamp_utc": "2026-10-12T23:45:40Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T23:46:00Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T23:46:27Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T23:46:44Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T23:48:30Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T23:48:34Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-12T23:48:41Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-12T23:48:41Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.