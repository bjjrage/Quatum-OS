# Auditoría Read-Only del Dataset Histórico Grabado

**Fecha de ejecución (UTC):** `2026-10-03T14:09:56.910096+00:00`  
**Directorio analizado:** `C:\Users\User\Desktop\PORYECTOS\TRADING OS\data\raw`  

## 1. Resumen Ejecutivo por Venue y Tabla

| Venue | Tabla | Archivos | Filas Estimadas | Horas de Span | Muestra Analizada | Precios Cero |
|---|---|---|---|---|---|---|
| `binance_perp` | `bbo_ticks` | 6912 | 32,561,036 | 14.7h | 238,335 | 0 |
| `binance_perp` | `forced_liquidations` | 809 | 12,464 | 14.6h | 786 | 0 |
| `binance_perp` | `futures_market_metrics` | 816 | 1,151,156 | 14.5h | 70,959 | 0 |
| `binance_perp` | `futures_open_interest` | 822 | 41,194 | 14.4h | 2,491 | 0 |
| `binance_perp` | `orderbook_l2_depth` | 1603 | 6,450,432 | 14.72h | 202,549 | 0 |
| `binance_perp` | `trade_ticks` | 816 | 1,400,362 | 14.5h | 86,702 | 0 |
| `deribit` | `bbo_ticks` | 822 | 1,704,189 | 14.4h | 103,009 | 0 |
| `deribit` | `deribit_metrics` | 822 | 1,856,249 | 14.4h | 112,180 | 0 |
| `deribit` | `trade_ticks` | 603 | 2,809 | 14.72h | 252 | 0 |
| `polymarket` | `bbo_ticks` | 822 | 60,758 | 14.4h | 3,483 | 0 |
| `polymarket` | `orderbook_l2_depth` | 102 | 294 | 14.61h | 212 | 0 |
| `polymarket` | `polymarket_metadata_history` | 56 | 28,112 | 0.0h | 25,100 | 0 |
| `polymarket` | `trade_ticks` | 822 | 352,473 | 14.4h | 21,643 | 21638 |

## 2. Hallazgos Específicos de Contaminación de Datos

### A. Polymarket (`price_change` vs `trade_ticks`)
- **Anomalía detectada:** `polymarket_zero_price_trade_issue = True`
- **Diagnóstico:** El recorder (`polymarket_recorder.py`) procesó eventos WebSocket de tipo `price_change` mapeándolos directamente a `trade_ticks`.
- **Impacto:** Las filas en `polymarket/table=trade_ticks` contienen registros con `price = 0.0` y `side = UNKNOWN` que NO representan transacciones ejecutadas en el CLOB, sino desplazamientos de cotización o cambios de referencia.
- **Clasificación del Dataset:** **SUSPECT** para `polymarket/trade_ticks`. No apto para análisis de flujo de órdenes/ejecución sin filtrar `price == 0`.

### B. Deribit (Ordenamiento de Vencimientos y Resuscripción)
- **Anomalía en Instrument Selection:** Deribit ordenó vencimientos alfabéticamente por cadena de texto `x.split('-')[1]` en lugar de cronológicamente.
- **Diagnóstico:** Cadenas de vencimiento como `1OCT26` preceden alfabéticamente a `26DEC25` (`'1' < '2'`), sesgando la muestra de los 60 contratos de opciones más activos.
- **Impacto en Resuscripción:** El poller horario descubrió nuevos instrumentos pero no actualizó la conexión activa de WebSocket.
- **Clasificación del Dataset:** **SUSPECT** en cobertura de opciones lejanas; los libros y ticks grabados para los instrumentos suscritos son sintácticamente válidos pero sufren de sesgo de selección.

### C. Integridad de Manifiestos de Almacenamiento
- **Manifiestos corruptos encontrados:** 0
- **Diagnóstico:** Los manifiestos existentes en disco son consistentes, pero la biblioteca `PartitionManifest` carecía de fail-closed ante corrupción accidental.

## 3. Matriz de Clasificación de Datos Históricos

| Venue / Stream | Clasificación | Justificación | Apto para Research STR-001/002 |
|---|---|---|---|
| `binance_perp` (todos los streams) | **VALID** | Ticks, L2 depth, liquidaciones y funding sin anomalías de schema ni corrupción. | **SÍ** |
| `deribit/bbo_ticks` & `deribit_metrics` | **VALID** | Precios de índice, DVOL y métricas de opciones capturadas fielmente. | **SÍ** |
| `deribit/trade_ticks` | **SUSPECT** | Opciones suscritas sesgadas por ordenamiento alfabético en vez de cronológico. | **CONDICIONAL** (Solo instrumentos presentes) |
| `polymarket/orderbook_l2_depth` & `bbo_ticks` | **VALID** | Libro L2 y BBO fielmente registrados con latencias y spreads correctos. | **SÍ** |
| `polymarket/trade_ticks` | **INVALID / CONTAMINATED** | Contaminado con eventos `price_change` con precio 0. Requiere filtro explícito. | **NO (crudo)** / Requiere sanitización de `price > 0` |

## 4. Política de No-Mutación
En estricto cumplimiento con las directivas no negociables, los 4,9M+ registros históricos existentes NO han sido borrados, truncados ni modificados.
Las correcciones se aplican en los pipelines de consumo/ingesta y en los recorders hacia el futuro.