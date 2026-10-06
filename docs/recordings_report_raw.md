# Reporte de recordings: `C:\Users\User\Desktop\PORYECTOS\TRADING OS\data\raw`

Total: 18 tablas, 139180 archivos (16 corruptos), 482,381,745 filas válidas, 9.26 GB en disco

## binance_perp / bbo_ticks

- Archivos: 56708 (5 corruptos/truncados) | Tamaño en disco: 4001.4 MB | Tamaño medio por archivo: 68.9 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791168528179392600…` 2026-10-05 02:48:48 (85850 B); `part-1791235166210543000…` 2026-10-05 21:19:26 (77768 B); `part-1791235176109188500…` 2026-10-05 21:19:36 (19005 B); `part-1791235177979641400…` 2026-10-05 21:19:37 (70797 B); `part-1791235182835963900…` 2026-10-05 21:19:42 (77147 B)
- Filas: 272,054,544
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `observed_event_age_ns` BIGINT, `venue` VARCHAR, `symbol` VARCHAR, `bid_price` DOUBLE, `bid_size` DOUBLE, `ask_price` DOUBLE, `ask_size` DOUBLE, `spread` DOUBLE, `capture_source` VARCHAR, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-10-02 23:08:20 UTC | hasta 2026-10-06 22:10:05 UTC | nulos 0
- Mayores huecos entre eventos: 8.11 h (termina 2026-10-05 10:55 UTC); 3.01 h (termina 2026-10-06 00:20 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 1.41 h (termina 2026-10-03 23:14 UTC); 1.26 h (termina 2026-10-03 01:45 UTC); 27.9 min (termina 2026-10-06 04:04 UTC); 15.3 min (termina 2026-10-04 03:32 UTC); 4.1 min (termina 2026-10-06 01:48 UTC)

## binance_perp / depth_snapshots

- Archivos: 608 (0 corruptos/truncados) | Tamaño en disco: 4.1 MB | Tamaño medio por archivo: 6.5 KB
- Filas: 21,239
- Columnas: `ts_utc_ns` BIGINT, `symbol` VARCHAR, `mid` DOUBLE, `spread_bps` DOUBLE, `bid_usd_05` DOUBLE, `ask_usd_05` DOUBLE, `imbalance_05` DOUBLE, `bid_usd_1` DOUBLE, `ask_usd_1` DOUBLE, `imbalance_1` DOUBLE, `open_interest` DOUBLE, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_utc_ns` | desde 2026-10-05 01:41:19 UTC | hasta 2026-10-06 22:06:07 UTC | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos entre eventos: 8.17 h (termina 2026-10-05 10:55 UTC); 2.30 h (termina 2026-10-05 23:34 UTC); 1.57 h (termina 2026-10-06 03:33 UTC); 29.6 min (termina 2026-10-06 04:04 UTC); 15.0 min (termina 2026-10-06 00:21 UTC); 13.1 min (termina 2026-10-06 00:00 UTC); 8.7 min (termina 2026-10-06 01:48 UTC); 6.5 min (termina 2026-10-06 01:20 UTC)

## binance_perp / forced_liquidations

- Archivos: 4622 (1 corruptos/truncados) | Tamaño en disco: 19.7 MB | Tamaño medio por archivo: 4.2 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235117817552100…` 2026-10-05 21:18:37 (4293 B)
- Filas: 83,121
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `symbol` VARCHAR, `pair_symbol` VARCHAR, `symbol_type` INTEGER, `side` VARCHAR, `price` DOUBLE, `orig_qty` DOUBLE, `executed_qty` DOUBLE, `is_partial_proxy` BOOLEAN, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-10-02 23:08:54 UTC | hasta 2026-10-06 22:09:06 UTC | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos entre eventos: 8.13 h (termina 2026-10-05 10:55 UTC); 3.04 h (termina 2026-10-06 00:20 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 1.42 h (termina 2026-10-03 23:14 UTC); 1.28 h (termina 2026-10-03 01:45 UTC); 28.2 min (termina 2026-10-06 04:04 UTC); 16.5 min (termina 2026-10-04 03:33 UTC); 4.3 min (termina 2026-10-06 01:48 UTC)

## binance_perp / futures_market_metrics

- Archivos: 4679 (1 corruptos/truncados) | Tamaño en disco: 89.4 MB | Tamaño medio por archivo: 18.7 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235117814535200…` 2026-10-05 21:18:37 (20319 B)
- Filas: 6,797,472
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `symbol` VARCHAR, `mark_price` DOUBLE, `index_price` DOUBLE, `funding_rate` DOUBLE, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-10-02 23:08:21 UTC | hasta 2026-10-06 22:10:07 UTC | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos entre eventos: 8.13 h (termina 2026-10-05 10:55 UTC); 3.03 h (termina 2026-10-06 00:20 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 1.41 h (termina 2026-10-03 23:14 UTC); 1.27 h (termina 2026-10-03 01:45 UTC); 28.0 min (termina 2026-10-06 04:04 UTC); 16.2 min (termina 2026-10-04 03:33 UTC); 4.3 min (termina 2026-10-06 01:48 UTC)

## binance_perp / futures_open_interest

- Archivos: 4709 (1 corruptos/truncados) | Tamaño en disco: 18.8 MB | Tamaño medio por archivo: 3.9 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235117581979700…` 2026-10-05 21:18:37 (4006 B)
- Filas: 235,747
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `symbol` VARCHAR, `open_interest` DOUBLE, `is_stale` BOOLEAN, `poll_latency_ms` DOUBLE, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-10-02 23:07:47 UTC | hasta 2026-10-06 22:10:00 UTC | nulos 2890
- Filas duplicadas exactas: 0
- Mayores huecos entre eventos: 8.12 h (termina 2026-10-05 10:55 UTC); 3.03 h (termina 2026-10-06 00:20 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 1.41 h (termina 2026-10-03 23:14 UTC); 1.27 h (termina 2026-10-03 01:45 UTC); 28.1 min (termina 2026-10-06 04:03 UTC); 16.2 min (termina 2026-10-04 03:32 UTC); 4.2 min (termina 2026-10-06 01:48 UTC)

## binance_perp / orderbook_l2_depth

- Archivos: 9478 (1 corruptos/truncados) | Tamaño en disco: 1577.1 MB | Tamaño medio por archivo: 162.5 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235152894047100…` 2026-10-05 21:19:12 (103136 B)
- Filas: 39,174,651
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `venue` VARCHAR, `symbol` VARCHAR, `bids_price` DOUBLE[], `bids_size` DOUBLE[], `asks_price` DOUBLE[], `asks_size` DOUBLE[], `depth_level` INTEGER, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-10-02 23:08:20 UTC | hasta 2026-10-06 22:10:07 UTC | nulos 0
- Mayores huecos entre eventos: 8.12 h (termina 2026-10-05 10:55 UTC); 3.02 h (termina 2026-10-06 00:20 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 1.41 h (termina 2026-10-03 23:14 UTC); 1.26 h (termina 2026-10-03 01:45 UTC); 28.0 min (termina 2026-10-06 04:04 UTC); 15.5 min (termina 2026-10-04 03:32 UTC); 4.3 min (termina 2026-10-06 01:48 UTC)

## binance_perp / trade_ticks

- Archivos: 5061 (1 corruptos/truncados) | Tamaño en disco: 302.8 MB | Tamaño medio por archivo: 58.4 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235117795889200…` 2026-10-05 21:18:37 (44849 B)
- Filas: 11,948,961
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `observed_event_age_ns` BIGINT, `venue` VARCHAR, `symbol` VARCHAR, `trade_id` VARCHAR, `side` VARCHAR, `price` DOUBLE, `size` DOUBLE, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-10-02 23:08:20 UTC | hasta 2026-10-06 22:10:07 UTC | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos entre eventos: 8.12 h (termina 2026-10-05 10:55 UTC); 3.03 h (termina 2026-10-06 00:20 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 1.41 h (termina 2026-10-03 23:14 UTC); 1.27 h (termina 2026-10-03 01:45 UTC); 28.0 min (termina 2026-10-06 04:04 UTC); 16.2 min (termina 2026-10-04 03:33 UTC); 4.3 min (termina 2026-10-06 01:48 UTC)

## deribit / bbo_ticks

- Archivos: 4707 (1 corruptos/truncados) | Tamaño en disco: 127.1 MB | Tamaño medio por archivo: 26.4 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235117695961700…` 2026-10-05 21:18:37 (24976 B)
- Filas: 11,695,794
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `observed_event_age_ns` BIGINT, `venue` VARCHAR, `symbol` VARCHAR, `bid_price` DOUBLE, `bid_size` DOUBLE, `ask_price` DOUBLE, `ask_size` DOUBLE, `spread` DOUBLE, `capture_source` VARCHAR, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-10-02 23:08:10 UTC | hasta 2026-10-06 22:10:06 UTC | nulos 0
- Filas duplicadas exactas: 12
- Mayores huecos entre eventos: 8.13 h (termina 2026-10-05 10:55 UTC); 3.03 h (termina 2026-10-06 00:20 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 1.41 h (termina 2026-10-03 23:14 UTC); 1.27 h (termina 2026-10-03 01:45 UTC); 28.0 min (termina 2026-10-06 04:04 UTC); 16.1 min (termina 2026-10-04 03:32 UTC); 4.3 min (termina 2026-10-06 01:48 UTC)

## deribit / deribit_metrics

- Archivos: 4711 (1 corruptos/truncados) | Tamaño en disco: 344.4 MB | Tamaño medio por archivo: 71.4 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235117677189400…` 2026-10-05 21:18:37 (67302 B)
- Filas: 12,684,366
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `instrument_name` VARCHAR, `underlying_price` DOUBLE, `mark_price` DOUBLE, `mark_iv` DOUBLE, `bid_iv` DOUBLE, `ask_iv` DOUBLE, `delta` DOUBLE, `gamma` DOUBLE, `vega` DOUBLE, `theta` DOUBLE, `underlying_index_price` DOUBLE, `dvol_index` DOUBLE, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-10-02 23:08:10 UTC | hasta 2026-10-06 22:10:06 UTC | nulos 0
- Filas duplicadas exactas: 2
- Mayores huecos entre eventos: 8.12 h (termina 2026-10-05 10:55 UTC); 3.03 h (termina 2026-10-06 00:20 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 1.41 h (termina 2026-10-03 23:14 UTC); 1.27 h (termina 2026-10-03 01:45 UTC); 28.0 min (termina 2026-10-06 04:04 UTC); 16.1 min (termina 2026-10-04 03:32 UTC); 4.2 min (termina 2026-10-06 01:48 UTC)

## deribit / trade_ticks

- Archivos: 3525 (1 corruptos/truncados) | Tamaño en disco: 12.3 MB | Tamaño medio por archivo: 3.4 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235117827097400…` 2026-10-05 21:18:37 (3762 B)
- Filas: 18,344
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `observed_event_age_ns` BIGINT, `venue` VARCHAR, `symbol` VARCHAR, `trade_id` VARCHAR, `side` VARCHAR, `price` DOUBLE, `size` DOUBLE, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-10-02 23:08:47 UTC | hasta 2026-10-06 22:09:59 UTC | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos entre eventos: 8.13 h (termina 2026-10-05 10:55 UTC); 3.05 h (termina 2026-10-06 00:20 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 1.44 h (termina 2026-10-03 23:14 UTC); 1.35 h (termina 2026-10-03 01:49 UTC); 31.6 min (termina 2026-10-06 04:06 UTC); 23.0 min (termina 2026-10-04 03:33 UTC); 13.5 min (termina 2026-10-04 03:58 UTC)

## polymarket / bbo_ticks

- Archivos: 26279 (1 corruptos/truncados) | Tamaño en disco: 1317.7 MB | Tamaño medio por archivo: 49.0 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235145993548300…` 2026-10-05 21:19:05 (59755 B)
- Filas: 116,125,895
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `observed_event_age_ns` BIGINT, `venue` VARCHAR, `symbol` VARCHAR, `bid_price` DOUBLE, `bid_size` DOUBLE, `ask_price` DOUBLE, `ask_size` DOUBLE, `spread` DOUBLE, `capture_source` VARCHAR, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-09-28 04:00:19 UTC | hasta 2026-10-06 22:10:07 UTC | nulos 0
- Mayores huecos entre eventos: 64.49 h (termina 2026-09-30 20:29 UTC); 43.88 h (termina 2026-10-02 20:25 UTC); 4.04 h (termina 2026-10-01 00:32 UTC); 1.81 h (termina 2026-10-05 08:15 UTC); 1.80 h (termina 2026-10-05 06:26 UTC); 1.77 h (termina 2026-10-02 22:11 UTC); 1.21 h (termina 2026-10-05 04:00 UTC); 1.02 h (termina 2026-10-03 22:51 UTC)

## polymarket / orderbook_l2_depth

- Archivos: 3458 (1 corruptos/truncados) | Tamaño en disco: 440.1 MB | Tamaño medio por archivo: 124.3 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235117608141500…` 2026-10-05 21:18:37 (141268 B)
- Filas: 4,307,499
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `venue` VARCHAR, `symbol` VARCHAR, `bids_price` DOUBLE[], `bids_size` DOUBLE[], `asks_price` DOUBLE[], `asks_size` DOUBLE[], `depth_level` INTEGER, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-09-28 04:00:19 UTC | hasta 2026-10-06 22:10:07 UTC | nulos 0
- Filas duplicadas exactas: 2
- Mayores huecos entre eventos: 64.48 h (termina 2026-09-30 20:29 UTC); 43.88 h (termina 2026-10-02 20:25 UTC); 4.04 h (termina 2026-10-01 00:32 UTC); 1.81 h (termina 2026-10-05 08:15 UTC); 1.80 h (termina 2026-10-05 06:26 UTC); 1.77 h (termina 2026-10-02 22:11 UTC); 1.22 h (termina 2026-10-05 04:00 UTC); 1.08 h (termina 2026-10-03 00:57 UTC)

## polymarket / polymarket_metadata_history

- Archivos: 684 (0 corruptos/truncados) | Tamaño en disco: 32.0 MB | Tamaño medio por archivo: 45.7 KB
- Filas: 216,091
- Columnas: `ts_polled_utc_ns` BIGINT, `market_id` VARCHAR, `condition_id` VARCHAR, `question` VARCHAR, `resolution_source` VARCHAR, `end_date_iso` VARCHAR, `fee_schedule_raw_json` VARCHAR, `fee_model_version` VARCHAR, `status` VARCHAR, `clob_token_ids_json` VARCHAR, `outcomes_json` VARCHAR, `description` VARCHAR, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_polled_utc_ns` | desde 2026-10-02 23:08:14 UTC | hasta 2026-10-06 22:05:04 UTC | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos entre eventos: 8.16 h (termina 2026-10-05 10:55 UTC); 3.07 h (termina 2026-10-06 00:20 UTC); 1.56 h (termina 2026-10-06 03:33 UTC); 1.46 h (termina 2026-10-03 23:14 UTC); 1.38 h (termina 2026-10-03 01:45 UTC); 30.3 min (termina 2026-10-04 03:32 UTC); 28.3 min (termina 2026-10-06 04:04 UTC); 15.2 min (termina 2026-10-04 12:01 UTC)

## polymarket / trade_ticks

- Archivos: 3881 (1 corruptos/truncados) | Tamaño en disco: 38.2 MB | Tamaño medio por archivo: 9.6 KB
- Archivos corruptos (hora UTC sacada del nombre): `part-1791235057489615600…` 2026-10-05 21:17:37 (4219 B)
- Filas: 735,294
- Columnas: `ts_exchange_ns` BIGINT, `ts_received_utc_ns` BIGINT, `ts_received_mono_ns` BIGINT, `observed_event_age_ns` BIGINT, `venue` VARCHAR, `symbol` VARCHAR, `trade_id` VARCHAR, `side` VARCHAR, `price` DOUBLE, `size` DOUBLE, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_exchange_ns` | desde 2026-10-02 23:08:19 UTC | hasta 2026-10-06 22:09:05 UTC | nulos 0
- Filas duplicadas exactas: 64,555
- Mayores huecos entre eventos: 8.15 h (termina 2026-10-05 10:55 UTC); 3.06 h (termina 2026-10-06 00:20 UTC); 1.59 h (termina 2026-10-03 23:25 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 1.27 h (termina 2026-10-03 01:45 UTC); 55.9 min (termina 2026-10-04 03:33 UTC); 52.0 min (termina 2026-10-04 00:42 UTC); 28.1 min (termina 2026-10-06 04:04 UTC)

## pumpfun / pumpfun_completes

- Archivos: 1114 (0 corruptos/truncados) | Tamaño en disco: 3.7 MB | Tamaño medio por archivo: 3.3 KB
- Filas: 1,708
- Columnas: `ts_received_utc_ns` BIGINT, `slot` BIGINT, `signature` VARCHAR, `mint` VARCHAR, `user` VARCHAR, `bonding_curve` VARCHAR, `ts_chain_s` BIGINT, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_received_utc_ns` | desde 2026-10-05 00:56:16 UTC | hasta 2026-10-06 22:10:14 UTC | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos entre eventos: 8.15 h (termina 2026-10-05 10:56 UTC); 2.29 h (termina 2026-10-05 23:35 UTC); 2.10 h (termina 2026-10-06 04:05 UTC); 13.2 min (termina 2026-10-06 01:50 UTC); 11.2 min (termina 2026-10-06 01:26 UTC); 11.0 min (termina 2026-10-05 12:06 UTC); 10.7 min (termina 2026-10-06 00:01 UTC); 9.2 min (termina 2026-10-06 00:20 UTC)

## pumpfun / pumpfun_creates

- Archivos: 1938 (0 corruptos/truncados) | Tamaño en disco: 27.9 MB | Tamaño medio por archivo: 14.0 KB
- Filas: 73,976
- Columnas: `ts_received_utc_ns` BIGINT, `slot` BIGINT, `signature` VARCHAR, `mint` VARCHAR, `name` VARCHAR, `symbol` VARCHAR, `uri` VARCHAR, `bonding_curve` VARCHAR, `user` VARCHAR, `creator` VARCHAR, `ts_chain_s` BIGINT, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_received_utc_ns` | desde 2026-10-05 00:55:56 UTC | hasta 2026-10-06 22:10:10 UTC | nulos 0
- Filas duplicadas exactas: 6
- Mayores huecos entre eventos: 8.11 h (termina 2026-10-05 10:55 UTC); 2.26 h (termina 2026-10-05 23:34 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 28.0 min (termina 2026-10-06 04:04 UTC); 9.0 min (termina 2026-10-06 00:20 UTC); 8.9 min (termina 2026-10-06 00:00 UTC); 4.5 min (termina 2026-10-06 01:48 UTC); 3.4 min (termina 2026-10-06 01:20 UTC)

## pumpfun / pumpfun_trades

- Archivos: 2002 (0 corruptos/truncados) | Tamaño en disco: 891.7 MB | Tamaño medio por archivo: 435.0 KB
- Filas: 6,202,499
- Columnas: `ts_received_utc_ns` BIGINT, `slot` BIGINT, `signature` VARCHAR, `mint` VARCHAR, `user` VARCHAR, `is_buy` BOOLEAN, `sol_amount` BIGINT, `token_amount` BIGINT, `ts_chain_s` BIGINT, `virtual_sol_reserves` BIGINT, `virtual_token_reserves` BIGINT, `real_sol_reserves` BIGINT, `real_token_reserves` BIGINT, `creator` VARCHAR, `fee` BIGINT, `creator_fee` BIGINT, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_received_utc_ns` | desde 2026-10-05 00:55:54 UTC | hasta 2026-10-06 22:10:14 UTC | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos entre eventos: 8.11 h (termina 2026-10-05 10:55 UTC); 2.26 h (termina 2026-10-05 23:34 UTC); 1.52 h (termina 2026-10-06 03:33 UTC); 27.9 min (termina 2026-10-06 04:04 UTC); 9.0 min (termina 2026-10-06 00:20 UTC); 8.9 min (termina 2026-10-06 00:00 UTC); 4.2 min (termina 2026-10-06 01:48 UTC); 3.3 min (termina 2026-10-06 01:20 UTC)

## pumpfun / x_mentions

- Archivos: 1016 (0 corruptos/truncados) | Tamaño en disco: 7.3 MB | Tamaño medio por archivo: 7.0 KB
- Filas: 4,544
- Columnas: `ts_query_utc_ns` BIGINT, `mint` VARCHAR, `symbol` VARCHAR, `name` VARCHAR, `token_age_s` BIGINT, `unique_buyers_5m` BIGINT, `net_buy_sol_5m` DOUBLE, `posts_found` BIGINT, `earliest_post_utc` VARCHAR, `accounts_json` VARCHAR, `max_followers` BIGINT, `total_followers` BIGINT, `has_large_account` BOOLEAN, `coordinated_shilling` BOOLEAN, `summary` VARCHAR, `cost_usd` DOUBLE, `model` VARCHAR, `x_status` VARCHAR, `consumer` VARCHAR, `query_version` VARCHAR, `query_hash` VARCHAR, `request_id` VARCHAR, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_query_utc_ns` | desde 2026-10-05 01:26:04 UTC | hasta 2026-10-06 22:10:02 UTC | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos entre eventos: 8.53 h (termina 2026-10-05 10:56 UTC); 7.08 h (termina 2026-10-06 04:05 UTC); 1.00 h (termina 2026-10-05 12:00 UTC); 1.00 h (termina 2026-10-05 14:00 UTC); 1.00 h (termina 2026-10-05 18:00 UTC); 1.00 h (termina 2026-10-05 16:00 UTC); 59.7 min (termina 2026-10-05 17:00 UTC); 59.7 min (termina 2026-10-05 20:00 UTC)
