# Snapshot Quant OS — 2026-10-10 22:51 UTC

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

- baja_vol: actualizado hace 0.2 min
- btc_tendencia: actualizado hace 0.2 min
- carry_funding: actualizado hace 0.2 min
- combinada: actualizado hace 0.2 min
- examen_2x: actualizado hace 0.2 min
- flujo_7d: actualizado hace 0.2 min
- flujo_reg200: actualizado hace 0.2 min
- flujo_v1: actualizado hace 0.2 min
- lider_azar: actualizado hace 0.2 min
- lider_corto: actualizado hace 0.2 min
- lider_sin_x: actualizado hace 0.2 min
- lider_x: actualizado hace 0.2 min
- mezcla_flujo_carry: actualizado hace 0.2 min
- poly_updown: actualizado hace 4726.9 min
- pump_azar: actualizado hace 5607.0 min
- pump_billeteras: actualizado hace 5607.0 min
- pump_billeteras_2x: actualizado hace 5607.0 min
- pump_billeteras_azar: actualizado hace 5607.0 min
- pump_detector_tarde: actualizado hace 5607.0 min
- pump_grupo: actualizado hace 5607.0 min
- pump_grupo_aguantar: actualizado hace 5607.0 min
- pump_grupo_nicho: actualizado hace 5607.0 min
- pump_nicho: actualizado hace 5607.0 min
- pump_nicho_azar: actualizado hace 5607.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 540 | -1.1 |
| binance_perp/depth_snapshots | 18 | 0.9 |
| binance_perp/forced_liquidations | 57 | -1.0 |
| binance_perp/futures_market_metrics | 61 | -1.0 |
| binance_perp/futures_open_interest | 61 | -1.0 |
| binance_perp/futures_positioning | 62 | -1.1 |
| binance_perp/orderbook_l2_depth | 118 | -1.6 |
| binance_perp/trade_ticks | 61 | -1.0 |
| deribit/bbo_ticks | 62 | -2.0 |
| deribit/deribit_metrics | 63 | -3.0 |
| deribit/trade_ticks | 36 | -2.0 |
| dexscreener/token_boosts | 2 | 20.3 |
| dexscreener/token_prices | 61 | -2.8 |
| dexscreener/token_profiles | 13 | 1.2 |
| limitless/limitless_book | 63 | -2.8 |
| limitless/limitless_markets | 12 | -0.8 |
| polymarket/bbo_ticks | 704 | -5.4 |
| polymarket/orderbook_l2_depth | 65 | -5.1 |
| polymarket/polymarket_metadata_history | 18 | -5.1 |
| polymarket/trade_ticks | 59 | -5.1 |
| pumpfun/creator_funding | 66 | -5.8 |
| pumpfun/pumpfun_completes | 42 | -5.8 |
| pumpfun/pumpfun_creates | 66 | -5.8 |
| pumpfun/pumpfun_trades | 66 | -5.8 |
| pumpfun/x_mentions | 0 | 5607.0 |
| telegram/calls | 7 | -1.8 |

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
{"timestamp_utc": "2026-10-10T22:40:23Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-10T22:42:30Z", "level": "WARNING", "logger": "polymarket_recorder", "message": "Polymarket WS disconnected: received 1013 (try again later) slow consumer: send buffer full; then sent 1013 (try again later) slow consumer: send buffer full. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T22:46:24Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T22:53:53Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T22:53:57Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-10T22:54:14Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-10T22:54:36Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
{"timestamp_utc": "2026-10-10T22:54:49Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.