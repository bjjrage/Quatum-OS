# Snapshot Quant OS — 2026-10-13 00:51 UTC

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

- baja_vol: actualizado hace 1.6 min
- btc_tendencia: actualizado hace 1.6 min
- carry_funding: actualizado hace 1.6 min
- combinada: actualizado hace 1.6 min
- examen_2x: actualizado hace 1.6 min
- flujo_7d: actualizado hace 1.6 min
- flujo_reg200: actualizado hace 1.6 min
- flujo_sectorial: actualizado hace 1.6 min
- flujo_v1: actualizado hace 1.6 min
- lider_azar: actualizado hace 1.6 min
- lider_corto: actualizado hace 1.6 min
- lider_sin_x: actualizado hace 1.6 min
- lider_x: actualizado hace 1.6 min
- mezcla_flujo_carry: actualizado hace 1.6 min
- poly_updown: actualizado hace 7727.0 min
- unlock_short_v1: actualizado hace 7.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 1771 | -2.5 |
| binance_perp/depth_snapshots | 20 | -0.1 |
| binance_perp/forced_liquidations | 62 | -2.2 |
| binance_perp/futures_market_metrics | 62 | -2.2 |
| binance_perp/futures_open_interest | 62 | -2.2 |
| binance_perp/futures_positioning | 63 | -2.1 |
| binance_perp/orderbook_l2_depth | 137 | -3.2 |
| binance_perp/trade_ticks | 170 | -3.2 |
| deribit/bbo_ticks | 63 | -3.2 |
| deribit/deribit_metrics | 67 | -3.2 |
| deribit/trade_ticks | 60 | -3.2 |
| dexscreener/token_boosts | 1 | 42.4 |
| dexscreener/token_prices | 62 | -3.8 |
| dexscreener/token_profiles | 14 | 3.3 |
| limitless/limitless_book | 64 | -3.8 |
| limitless/limitless_markets | 12 | 0.2 |
| polymarket/bbo_ticks | 974 | -4.7 |
| polymarket/orderbook_l2_depth | 64 | -4.2 |
| polymarket/polymarket_metadata_history | 17 | -4.2 |
| polymarket/trade_ticks | 58 | -4.2 |
| pumpfun/creator_funding | 65 | -4.8 |
| pumpfun/pumpfun_completes | 31 | -4.8 |
| pumpfun/pumpfun_creates | 65 | -4.8 |
| pumpfun/pumpfun_trades | 65 | -4.8 |
| pumpfun/x_mentions | 0 | 8607.1 |
| telegram/calls | 16 | 2.3 |

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
{"timestamp_utc": "2026-10-13T00:54:03Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-13T00:54:24Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
{"timestamp_utc": "2026-10-13T00:54:46Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 3.4s..."}
{"timestamp_utc": "2026-10-13T00:55:02Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T00:55:45Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-13T00:55:49Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-13T00:56:07Z", "level": "WARNING", "logger": "binance_oi_poller", "message": "Recorded stale Open Interest for ADAUSDT due to polling failure."}
{"timestamp_utc": "2026-10-13T00:56:29Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.