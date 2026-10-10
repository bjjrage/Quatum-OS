# Snapshot Quant OS — 2026-10-10 00:51 UTC

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
- flujo_v1: actualizado hace 1.1 min
- lider_azar: actualizado hace 1.1 min
- lider_corto: actualizado hace 1.1 min
- lider_sin_x: actualizado hace 1.1 min
- lider_x: actualizado hace 1.1 min
- poly_updown: actualizado hace 3406.8 min
- pump_azar: actualizado hace 4287.0 min
- pump_billeteras: actualizado hace 4287.0 min
- pump_billeteras_2x: actualizado hace 4287.0 min
- pump_billeteras_azar: actualizado hace 4287.0 min
- pump_detector_tarde: actualizado hace 4287.0 min
- pump_grupo: actualizado hace 4287.0 min
- pump_grupo_aguantar: actualizado hace 4287.0 min
- pump_grupo_nicho: actualizado hace 4287.0 min
- pump_nicho: actualizado hace 4287.0 min
- pump_nicho_azar: actualizado hace 4287.0 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 576 | -0.4 |
| binance_perp/depth_snapshots | 17 | -0.2 |
| binance_perp/forced_liquidations | 59 | 0.3 |
| binance_perp/futures_market_metrics | 60 | 0.3 |
| binance_perp/futures_open_interest | 60 | 0.3 |
| binance_perp/orderbook_l2_depth | 120 | -0.3 |
| binance_perp/trade_ticks | 61 | 0.3 |
| deribit/bbo_ticks | 60 | 0.3 |
| deribit/deribit_metrics | 60 | 0.3 |
| deribit/trade_ticks | 42 | 0.3 |
| dexscreener/token_boosts | 3 | 7.8 |
| dexscreener/token_prices | 59 | -0.2 |
| dexscreener/token_profiles | 16 | 0.8 |
| limitless/limitless_book | 61 | -0.2 |
| limitless/limitless_markets | 14 | -0.2 |
| polymarket/bbo_ticks | 840 | -1.0 |
| polymarket/orderbook_l2_depth | 61 | -0.7 |
| polymarket/polymarket_metadata_history | 17 | 0.3 |
| polymarket/trade_ticks | 59 | -0.7 |
| pumpfun/creator_funding | 61 | -0.2 |
| pumpfun/pumpfun_completes | 33 | -0.2 |
| pumpfun/pumpfun_creates | 61 | -0.2 |
| pumpfun/pumpfun_trades | 61 | -0.2 |
| pumpfun/x_mentions | 0 | 4286.9 |
| telegram/calls | 3 | 25.9 |

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
{"timestamp_utc": "2026-10-10T00:35:49Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-10T00:36:26Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T00:42:44Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T00:42:55Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-10T00:43:06Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
{"timestamp_utc": "2026-10-10T00:46:16Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: received 4000 (private use) heartbeat close; then sent 4000 (private use) heartbeat close. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T00:49:51Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: received 4000 (private use) heartbeat close; then sent 4000 (private use) heartbeat close. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-10T00:50:02Z", "level": "WARNING", "logger": "deribit_recorder", "message": "Deribit WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
```

Detalle completo en latest.json.