# Snapshot Quant OS — 2026-10-08 02:51 UTC

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
- pumpfun_recorder: STOPPED
- pumpfun_paper: DISABLED
- leader_paper: STOPPED
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 166.4 min
- btc_tendencia: actualizado hace 163.1 min
- carry_funding: actualizado hace 166.4 min
- combinada: actualizado hace 166.4 min
- examen_2x: actualizado hace 166.4 min
- flujo_7d: actualizado hace 166.4 min
- flujo_v1: actualizado hace 166.4 min
- lider_azar: actualizado hace 166.4 min
- lider_corto: actualizado hace 166.4 min
- lider_sin_x: actualizado hace 166.4 min
- lider_x: actualizado hace 166.4 min
- poly_updown: actualizado hace 646.8 min
- pump_azar: actualizado hace 1526.9 min
- pump_billeteras: actualizado hace 1527.0 min
- pump_billeteras_2x: actualizado hace 1527.0 min
- pump_billeteras_azar: actualizado hace 1527.0 min
- pump_detector_tarde: actualizado hace 1526.9 min
- pump_grupo: actualizado hace 1526.9 min
- pump_grupo_aguantar: actualizado hace 1526.9 min
- pump_grupo_nicho: actualizado hace 1526.9 min
- pump_nicho: actualizado hace 1526.9 min
- pump_nicho_azar: actualizado hace 1526.9 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 0 | 163.2 |
| binance_perp/depth_snapshots | 0 | 169.2 |
| binance_perp/forced_liquidations | 0 | 163.2 |
| binance_perp/futures_market_metrics | 0 | 163.2 |
| binance_perp/futures_open_interest | 0 | 163.2 |
| binance_perp/orderbook_l2_depth | 0 | 163.2 |
| binance_perp/trade_ticks | 0 | 163.2 |
| deribit/bbo_ticks | 0 | 163.2 |
| deribit/deribit_metrics | 0 | 163.2 |
| deribit/trade_ticks | 0 | 163.2 |
| dexscreener/token_boosts | 0 | 163.3 |
| dexscreener/token_prices | 0 | 163.3 |
| dexscreener/token_profiles | 0 | 163.3 |
| limitless/limitless_book | 0 | 163.3 |
| limitless/limitless_markets | 0 | 165.3 |
| polymarket/bbo_ticks | 0 | 163.2 |
| polymarket/orderbook_l2_depth | 0 | 163.2 |
| polymarket/polymarket_metadata_history | 0 | 164.2 |
| polymarket/trade_ticks | 0 | 163.2 |
| pumpfun/creator_funding | 0 | 163.3 |
| pumpfun/pumpfun_completes | 0 | 163.3 |
| pumpfun/pumpfun_creates | 0 | 163.3 |
| pumpfun/pumpfun_trades | 0 | 163.3 |
| pumpfun/x_mentions | 0 | 1526.9 |
| telegram/calls | 0 | 164.3 |

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
{"timestamp_utc": "2026-10-08T00:05:42Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 5.1s..."}
{"timestamp_utc": "2026-10-08T00:06:00Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 5.1s..."}
{"timestamp_utc": "2026-10-08T00:06:07Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 7.6s..."}
{"timestamp_utc": "2026-10-08T00:06:46Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T00:06:49Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-08T00:07:44Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-08T00:07:48Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance REST fallback ON: WebSocket de precios ca\u00eddo, se piden precios por REST."}
{"timestamp_utc": "2026-10-08T00:08:05Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
```

Detalle completo en latest.json.