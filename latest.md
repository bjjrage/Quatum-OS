# Snapshot Quant OS — 2026-10-21 10:51 UTC

## Polymarket up/down (paper)

- Señales 425 · llenadas 291 · perdidas 134 (32% se las llevó otro)
- PnL Binance US$ 1817.40 · PnL oficial US$ -84.10 (291 resueltas) · aciertos 40% · t por ventana -0.8387298218090913
- Criterio: todavía no

## Salud

- api: STOPPED
- web: STOPPED
- os_launcher: STOPPED
- supervisor: ERROR
- markets_recorder: STOPPED
- paper_runtime: STOPPED
- pumpfun_recorder: DISABLED
- pumpfun_paper: DISABLED
- leader_paper: STOPPED
- x_watcher: DISABLED

## Papers (state.json)

- baja_vol: actualizado hace 609.3 min
- btc_tendencia: actualizado hace 609.3 min
- carry_funding: actualizado hace 609.3 min
- combinada: actualizado hace 609.3 min
- examen_2x: actualizado hace 10885.3 min
- flujo_7d: actualizado hace 609.3 min
- flujo_reg200: actualizado hace 609.3 min
- flujo_sectorial: actualizado hace 609.3 min
- flujo_v1: actualizado hace 609.3 min
- lider_azar: actualizado hace 609.3 min
- lider_corto: actualizado hace 609.3 min
- lider_sin_x: actualizado hace 609.3 min
- lider_x: actualizado hace 609.3 min
- mezcla_flujo_carry: actualizado hace 609.3 min
- poly_updown: actualizado hace 19846.9 min
- unlock_short_v1: actualizado hace 585.5 min

## Recorders (última hora)

| tabla | archivos | última escritura (min) |
|---|---|---|
| binance_perp/bbo_ticks | 0 | 609.3 |
| binance_perp/depth_snapshots | 0 | 609.3 |
| binance_perp/forced_liquidations | 0 | 609.3 |
| binance_perp/futures_market_metrics | 0 | 609.3 |
| binance_perp/futures_open_interest | 0 | 609.3 |
| binance_perp/futures_positioning | 0 | 609.3 |
| binance_perp/orderbook_l2_depth | 0 | 609.3 |
| binance_perp/trade_ticks | 0 | 609.3 |
| deribit/bbo_ticks | 0 | 10884.8 |
| deribit/deribit_metrics | 0 | 10884.8 |
| deribit/trade_ticks | 0 | 10885.8 |
| dexscreener/token_boosts | 0 | 10891.9 |
| dexscreener/token_prices | 0 | 10884.9 |
| dexscreener/token_profiles | 0 | 10886.9 |
| limitless/limitless_book | 0 | 10884.9 |
| limitless/limitless_markets | 0 | 10884.9 |
| polymarket/bbo_ticks | 0 | 10884.8 |
| polymarket/orderbook_l2_depth | 0 | 10884.8 |
| polymarket/polymarket_metadata_history | 0 | 10885.8 |
| polymarket/trade_ticks | 0 | 10884.8 |
| pumpfun/creator_funding | 0 | 10884.9 |
| pumpfun/pumpfun_completes | 0 | 10884.9 |
| pumpfun/pumpfun_creates | 0 | 10884.9 |
| pumpfun/pumpfun_trades | 0 | 10884.9 |
| pumpfun/x_mentions | 0 | 20727.0 |
| telegram/calls | 0 | 10885.9 |

## Problemas en logs (últimos)

### os_launcher.log
```
Traceback (most recent call last):
Traceback (most recent call last):
Traceback (most recent call last):
    update_health("os_launcher", "ERROR", error=f"{type(exc).__name__}: {exc}")
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
{"timestamp_utc": "2026-10-20T23:54:42Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 1.5s..."}
{"timestamp_utc": "2026-10-20T23:55:01Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
{"timestamp_utc": "2026-10-20T23:55:04Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 2.2s..."}
{"timestamp_utc": "2026-10-20T23:55:23Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: timed out during opening handshake. Reconnecting in 3.4s..."}
{"timestamp_utc": "2026-10-20T23:55:26Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance MARKET WS disconnected: timed out during opening handshake. Reconnecting in 3.4s..."}
{"timestamp_utc": "2026-10-21T00:28:40Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-21T00:32:26Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: sent 1011 (internal error) keepalive ping timeout; no close frame received. Reconnecting in 1.0s..."}
{"timestamp_utc": "2026-10-21T00:34:20Z", "level": "WARNING", "logger": "binance_recorder", "message": "Binance PUBLIC WS disconnected: no close frame received or sent. Reconnecting in 1.0s..."}
```

Detalle completo en latest.json.