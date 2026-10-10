# Snapshot Quant OS — 2026-10-10 21:51 UTC

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

- baja_vol: actualizado hace 0.5 min
- btc_tendencia: actualizado hace 0.5 min
- carry_funding: actualizado hace 0.5 min
- combinada: actualizado hace 0.5 min
- examen_2x: actualizado hace 0.5 min
- flujo_7d: actualizado hace 0.5 min
- flujo_reg200: actualizado hace 0.5 min
- flujo_v1: actualizado hace 0.5 min
- lider_azar: actualizado hace 0.5 min
- lider_corto: actualizado hace 0.5 min
- lider_sin_x: actualizado hace 0.5 min
- lider_x: actualizado hace 0.5 min
- mezcla_flujo_carry: actualizado hace 0.5 min
- poly_updown: actualizado hace 4666.9 min
- pump_azar: actualizado hace 5547.0 min
- pump_billeteras: actualizado hace 5547.0 min
- pump_billeteras_2x: actualizado hace 5547.0 min
- pump_billeteras_azar: actualizado hace 5547.0 min
- pump_detector_tarde: actualizado hace 5547.0 min
- pump_grupo: actualizado hace 5547.0 min
- pump_grupo_aguantar: actualizado hace 5547.0 min
- pump_grupo_nicho: actualizado hace 5547.0 min
- pump_nicho: actualizado hace 5547.0 min
- pump_nicho_azar: actualizado hace 5547.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 491 | -0.9 |
| binance_perp/depth_snapshots | 18 | -0.1 |
| binance_perp/forced_liquidations | 61 | -0.5 |
| binance_perp/futures_market_metrics | 61 | -0.5 |
| binance_perp/futures_open_interest | 61 | -0.5 |
| binance_perp/futures_positioning | 61 | -0.1 |
| binance_perp/orderbook_l2_depth | 121 | -1.1 |
| binance_perp/trade_ticks | 61 | -0.5 |
| deribit/bbo_ticks | 61 | -0.5 |
| deribit/deribit_metrics | 61 | -0.5 |
| deribit/trade_ticks | 35 | 0.5 |
| dexscreener/token_boosts | 4 | 15.4 |
| dexscreener/token_prices | 59 | 0.3 |
| dexscreener/token_profiles | 16 | 3.3 |
| limitless/limitless_book | 61 | -0.7 |
| limitless/limitless_markets | 13 | 0.3 |
| polymarket/bbo_ticks | 1389 | -2.1 |
| polymarket/orderbook_l2_depth | 64 | -1.5 |
| polymarket/polymarket_metadata_history | 17 | -0.5 |
| polymarket/trade_ticks | 62 | -1.5 |
| pumpfun/creator_funding | 62 | -1.7 |
| pumpfun/pumpfun_completes | 42 | -1.7 |
| pumpfun/pumpfun_creates | 62 | -1.7 |
| pumpfun/pumpfun_trades | 64 | -1.7 |
| pumpfun/x_mentions | 0 | 5547.0 |
| telegram/calls | 10 | 5.3 |

## Problemas en logs (últimos)

### api.log
```
{"timestamp_utc": "2026-10-10T20:47:14Z", "level": "ERROR", "logger": "flujo_paper", "message": "state.json ilegible: NO se sobrescribe; revisar a mano."}
```
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
{"timestamp_utc": "2026-10-10T19:00:27Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T19:55:09Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T19:55:10Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T19:55:28Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T20:33:04Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T20:55:11Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T20:55:15Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-10T20:55:44Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: received 4000 (private use) heartbeat close; then sent 4000 (private use) heartbeat close. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.