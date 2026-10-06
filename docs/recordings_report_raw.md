# Reporte de recordings: `C:\Users\User\Desktop\PORYECTOS\TRADING OS\data\raw`

Total: 18 tablas, 138821 archivos, 6,472,954 filas, 0.96 GB

## binance_perp / bbo_ticks

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/binance_perp/table=bbo_ticks/year=2026/month=10/day=05/hour=02/part-1791168528179392600-0fe6be7d.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (56565 archivos)

## binance_perp / depth_snapshots

- Archivos: 605 | Filas: 21,165 | Tamaño: 4.0 MB
- Columnas: `ts_utc_ns` BIGINT, `symbol` VARCHAR, `mid` DOUBLE, `spread_bps` DOUBLE, `bid_usd_05` DOUBLE, `ask_usd_05` DOUBLE, `imbalance_05` DOUBLE, `bid_usd_1` DOUBLE, `ask_usd_1` DOUBLE, `imbalance_1` DOUBLE, `open_interest` DOUBLE, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_utc_ns` | min `1791164479231638800` | max `1791323992294411700` | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos (unidad de la columna): 29,408,288,222,500 en 1791197730667401100; 8,279,853,485,300 en 1791243277855142700; 5,639,169,238,800 en 1791257621688969200; 1,773,101,692,700 en 1791259443286310400; 898,297,420,000 en 1791246117061098600

## binance_perp / forced_liquidations

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/binance_perp/table=forced_liquidations/year=2026/month=10/day=05/hour=21/part-1791235117817552100-1f4937f9.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (4613 archivos)

## binance_perp / futures_market_metrics

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/binance_perp/table=futures_market_metrics/year=2026/month=10/day=05/hour=21/part-1791235117814535200-a186a87a.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (4669 archivos)

## binance_perp / futures_open_interest

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/binance_perp/table=futures_open_interest/year=2026/month=10/day=05/hour=21/part-1791235117581979700-f43d0ffa.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (4699 archivos)

## binance_perp / orderbook_l2_depth

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/binance_perp/table=orderbook_l2_depth/year=2026/month=10/day=05/hour=21/part-1791235152894047100-faa11a53.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (9458 archivos)

## binance_perp / trade_ticks

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/binance_perp/table=trade_ticks/year=2026/month=10/day=05/hour=21/part-1791235117795889200-49e1888f.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (5051 archivos)

## deribit / bbo_ticks

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/deribit/table=bbo_ticks/year=2026/month=10/day=05/hour=21/part-1791235117695961700-c7f3c778.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (4697 archivos)

## deribit / deribit_metrics

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/deribit/table=deribit_metrics/year=2026/month=10/day=05/hour=21/part-1791235117677189400-3e90490e.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (4701 archivos)

## deribit / trade_ticks

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/deribit/table=trade_ticks/year=2026/month=10/day=05/hour=21/part-1791235117827097400-ddf6d6ad.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (3517 archivos)

## polymarket / bbo_ticks

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/polymarket/table=bbo_ticks/year=2026/month=10/day=05/hour=21/part-1791235145993548300-82002e5a.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (26213 archivos)

## polymarket / orderbook_l2_depth

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/polymarket/table=orderbook_l2_depth/year=2026/month=10/day=05/hour=21/part-1791235117608141500-bae1b1a0.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (3448 archivos)

## polymarket / polymarket_metadata_history

- Archivos: 682 | Filas: 216,082 | Tamaño: 32.0 MB
- Columnas: `ts_polled_utc_ns` BIGINT, `market_id` VARCHAR, `condition_id` VARCHAR, `question` VARCHAR, `resolution_source` VARCHAR, `end_date_iso` VARCHAR, `fee_schedule_raw_json` VARCHAR, `fee_model_version` VARCHAR, `status` VARCHAR, `clob_token_ids_json` VARCHAR, `outcomes_json` VARCHAR, `description` VARCHAR, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_polled_utc_ns` | min `1790982494212156500` | max `1791323800966150300` | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos (unidad de la columna): 29,371,771,550,800 en 1791197730339896600; 11,058,553,494,300 en 1791246035519669400; 5,602,762,598,200 en 1791257620964706000; 5,238,717,096,700 en 1791069249960523700; 4,950,850,366,800 en 1790991947856074700

## polymarket / trade_ticks

ERROR leyendo: `Invalid Input Error: No magic bytes found at end of file 'C:/Users/User/Desktop/PORYECTOS/TRADING OS/data/raw/polymarket/table=trade_ticks/year=2026/month=10/day=05/hour=21/part-1791235057489615600-5253c90b.parquet'

LINE 1: DESCRIBE SELECT * FROM read_parquet(['C:/Users/User/Desktop/PORYECTOS/TRADING OS...
                               ^` (3873 archivos)

## pumpfun / pumpfun_completes

- Archivos: 1108 | Filas: 1,699 | Tamaño: 3.7 MB
- Columnas: `ts_received_utc_ns` BIGINT, `slot` BIGINT, `signature` VARCHAR, `mint` VARCHAR, `user` VARCHAR, `bonding_curve` VARCHAR, `ts_chain_s` BIGINT, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_received_utc_ns` | min `1791161776216169700` | max `1791323984111106400` | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos (unidad de la columna): 29,325,293,295,500 en 1791197776470473700; 8,226,128,857,300 en 1791243318747196300; 7,574,795,890,500 en 1791259523577422900; 789,789,746,400 en 1791251417903000800; 669,094,715,400 en 1791250006956207600

## pumpfun / pumpfun_creates

- Archivos: 1928 | Filas: 73,529 | Tamaño: 27.7 MB
- Columnas: `ts_received_utc_ns` BIGINT, `slot` BIGINT, `signature` VARCHAR, `mint` VARCHAR, `name` VARCHAR, `symbol` VARCHAR, `uri` VARCHAR, `bonding_curve` VARCHAR, `user` VARCHAR, `creator` VARCHAR, `ts_chain_s` BIGINT, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_received_utc_ns` | min `1791161756799086900` | max `1791324012341101300` | nulos 0
- Filas duplicadas exactas: 6
- Mayores huecos (unidad de la columna): 29,195,128,358,100 en 1791197731223646400; 8,134,049,225,400 en 1791243280754919500; 5,469,430,572,700 en 1791257623587025900; 1,678,714,251,400 en 1791259448660178500; 541,311,555,500 en 1791246039183641500

## pumpfun / pumpfun_trades

- Archivos: 1988 | Filas: 6,155,995 | Tamaño: 885.1 MB
- Columnas: `ts_received_utc_ns` BIGINT, `slot` BIGINT, `signature` VARCHAR, `mint` VARCHAR, `user` VARCHAR, `is_buy` BOOLEAN, `sol_amount` BIGINT, `token_amount` BIGINT, `ts_chain_s` BIGINT, `virtual_sol_reserves` BIGINT, `virtual_token_reserves` BIGINT, `real_sol_reserves` BIGINT, `real_token_reserves` BIGINT, `creator` VARCHAR, `fee` BIGINT, `creator_fee` BIGINT, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_received_utc_ns` | min `1791161754576624100` | max `1791324012858915400` | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos (unidad de la columna): 29,194,341,980,500 en 1791197730874193800; 8,130,436,155,400 en 1791243277709403300; 5,467,245,933,500 en 1791257621407975900; 1,673,199,971,400 en 1791259443206514800; 538,151,178,500 en 1791246036174836000

## pumpfun / x_mentions

- Archivos: 1006 | Filas: 4,484 | Tamaño: 7.3 MB
- Columnas: `ts_query_utc_ns` BIGINT, `mint` VARCHAR, `symbol` VARCHAR, `name` VARCHAR, `token_age_s` BIGINT, `unique_buyers_5m` BIGINT, `net_buy_sol_5m` DOUBLE, `posts_found` BIGINT, `earliest_post_utc` VARCHAR, `accounts_json` VARCHAR, `max_followers` BIGINT, `total_followers` BIGINT, `has_large_account` BOOLEAN, `coordinated_shilling` BOOLEAN, `summary` VARCHAR, `cost_usd` DOUBLE, `model` VARCHAR, `x_status` VARCHAR, `consumer` VARCHAR, `query_version` VARCHAR, `query_hash` VARCHAR, `request_id` VARCHAR, `day` VARCHAR, `hour` VARCHAR, `month` BIGINT, `table` VARCHAR, `year` BIGINT
- Columna de tiempo: `ts_query_utc_ns` | min `1791163564668910800` | max `1791324001465340300` | nulos 0
- Filas duplicadas exactas: 0
- Mayores huecos (unidad de la columna): 30,717,656,253,700 en 1791197793280304400; 25,488,400,774,400 en 1791259508527716100; 3,612,977,224,200 en 1791201633892841200; 3,608,587,331,700 en 1791208835109682100; 3,608,577,948,500 en 1791223219837878200
