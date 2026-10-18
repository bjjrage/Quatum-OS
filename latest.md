# Snapshot Quant OS — 2026-10-18 15:51 UTC

## Polymarket up/down (paper)

- Señales 425 · llenadas 291 · perdidas 134 (32% se las llevó otro)
- PnL Binance US$ 1817.40 · PnL oficial US$ -84.10 (291 resueltas) · aciertos 40% · t por ventana -0.8387298218090913
- Criterio: todavía no

## Salud

- api: STOPPED
- web: STOPPED
- os_launcher: STOPPED
- supervisor: STOPPED
- markets_recorder: STOPPED
- paper_runtime: STOPPED
- pumpfun_recorder: DISABLED
- pumpfun_paper: DISABLED
- leader_paper: STOPPED
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 597.4 min
- btc_tendencia: actualizado hace 597.4 min
- carry_funding: actualizado hace 597.4 min
- combinada: actualizado hace 597.4 min
- examen_2x: actualizado hace 6865.4 min
- flujo_7d: actualizado hace 597.4 min
- flujo_reg200: actualizado hace 597.4 min
- flujo_sectorial: actualizado hace 597.4 min
- flujo_v1: actualizado hace 597.4 min
- lider_azar: actualizado hace 597.4 min
- lider_corto: actualizado hace 597.4 min
- lider_sin_x: actualizado hace 597.4 min
- lider_x: actualizado hace 597.4 min
- mezcla_flujo_carry: actualizado hace 597.4 min
- poly_updown: actualizado hace 15826.9 min
- unlock_short_v1: actualizado hace 645.3 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 0 | 596.4 |
| binance_perp/depth_snapshots | 0 | 596.7 |
| binance_perp/forced_liquidations | 0 | 596.5 |
| binance_perp/futures_market_metrics | 0 | 596.5 |
| binance_perp/futures_open_interest | 0 | 596.5 |
| binance_perp/futures_positioning | 0 | 596.7 |
| binance_perp/orderbook_l2_depth | 0 | 596.5 |
| binance_perp/trade_ticks | 0 | 596.5 |
| deribit/bbo_ticks | 0 | 6864.8 |
| deribit/deribit_metrics | 0 | 6864.8 |
| deribit/trade_ticks | 0 | 6865.8 |
| dexscreener/token_boosts | 0 | 6872.0 |
| dexscreener/token_prices | 0 | 6864.9 |
| dexscreener/token_profiles | 0 | 6867.0 |
| limitless/limitless_book | 0 | 6864.9 |
| limitless/limitless_markets | 0 | 6864.9 |
| polymarket/bbo_ticks | 0 | 6864.8 |
| polymarket/orderbook_l2_depth | 0 | 6864.8 |
| polymarket/polymarket_metadata_history | 0 | 6865.9 |
| polymarket/trade_ticks | 0 | 6864.8 |
| pumpfun/creator_funding | 0 | 6864.9 |
| pumpfun/pumpfun_completes | 0 | 6864.9 |
| pumpfun/pumpfun_creates | 0 | 6864.9 |
| pumpfun/pumpfun_trades | 0 | 6864.9 |
| pumpfun/x_mentions | 0 | 16707.0 |
| telegram/calls | 0 | 6865.9 |

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
{"timestamp_utc": "2026-10-18T00:54:20Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-18T00:54:24Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-18T00:54:41Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-18T00:54:41Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-18T00:55:08Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-18T00:57:59Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-18T01:37:15Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-18T02:54:19Z", "level": "WARNING", "logger": "binance_oi_poller", "message": "Recorded stale Open Interest for BTCUSDT due to polling failure."}
```

Detalle completo en latest.json.