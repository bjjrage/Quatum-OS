# Auditoría pre-paper — Trading / Quant OS

3 de octubre de 2026 (segunda pasada, sobre el código del 3/10 a la noche)

**Veredicto: no está listo para empezar el paper trading.** El sistema sí está listo para seguir grabando datos, después de corregir tres detalles de los recorders. El motivo no es de calidad del código. No existe el circuito que haría el paper: nada toma datos en vivo, se los pasa a una estrategia, lleva la orden al router y ejecuta en el broker de paper. Además, STR-001 no tiene con qué calcular sus entradas.

Los 590 tests pasan (los corrí en una copia), pero ninguno cubre los puntos de esta auditoría.

## Estado de correcciones (aplicadas la misma noche)

Suite completa: **624 tests pasan** (590 originales + 34 nuevos). Verifiqué que los tests nuevos fallan con el código viejo y pasan con el corregido. **El recorder que está corriendo tiene que reiniciarse** para tomar los cambios.

| # | Estado | Qué se hizo |
| --- | --- | --- |
| 1 | **Parcial** | Nuevo runner en modo sombra para STR-001 (`scripts/run_str001_shadow.py`, `run_shadow.bat`). Lee Polymarket y Deribit por REST público, no envía órdenes y registra cada evaluación con todos sus insumos. El loop de paper con el router y el broker **sigue sin existir**. |
| 2 | **Corregido** (probado con datos sintéticos, no contra las APIs reales) | `src/research/market_mapping.py` parsea la pregunta y rechaza con motivo explícito los mercados de barrera ("hit/reach/dip"), los ambiguos y los de fecha dudosa. Resuelve a las 12:00 ET. `src/quant/deribit_surface.py` interpola la varianza total en el tiempo entre vencimientos, sin extrapolar. Acepta "arriba de", "debajo de" y rangos. |
| 3 | **Corregido en el código** | Snapshot REST del libro cada 60 s, registro de `price_change`, descubrimiento solo de mercados BTC/ETH/SOL, paginado, y los mercados cerrados se quitan del set activo. La metadata ahora guarda los token ids, los outcomes y las reglas de resolución. |
| 4 | **Corregido sin confirmar el bug** | Bids y asks se ordenan siempre mejor-primero, así que da igual cuál fuera el orden de llegada. Sigue pendiente correr la consulta SQL para saber cuántos datos ya grabados tienen el BBO mal. |
| 5 | **Corregido** | `is_risk_reducing` se mide contra la posición efectiva (llena más en vuelo), y una orden que cruza por cero no cuenta como reductora. |
| 6 | **Corregido (a, b, c)** | Un límite pasivo solo avanza o se llena con un trade al precio o mejor. La compra se recorta por caja y si no hay caja se rechaza. El PnL realizado es neto de comisiones. **(d) pendiente:** la firma del permiso todavía no incluye cantidad ni precio. |
| 7 | **Pendiente (tuyo)** | `w32tm /resync` en Windows y NTP activo. No se puede corregir desde el código. |
| 8 | **Corregido** | Filas y símbolos se asignan por venue según la carpeta, y las tablas sin columna `venue` (métricas de Deribit, open interest, metadata) ahora se cuentan. `PEPEUSDT` pasó a `1000PEPEUSDT`. |
| 9 | **Corregido** | Ver el hallazgo 3. |
| 10 | **Pendiente (tuyo)** | Mover el recorder y el shadow a un servidor que no se suspenda. |
| 11 | **Corregido** | El DSR usa la varianza real entre intentos (`trial_sharpes` en el contexto, tomada de `result_metrics["sharpe_per_period"]`). Sin esos datos mantiene el 1,0 anterior, que es conservador. |
| 12 | **Corregido** | `register()` rechaza cualquier etapa posterior a RESEARCH salvo `trusted_seed=True` (solo el cargador de semillas); avanzar exige `update_stage()` con evidencia. |
| 13 | **Corregido (import de `reconcile`)** | `/health` ahora es real (disco escribible + recorder activo; devuelve DEGRADED si no). El token de la UI no aplica: la UI solo lee y no llama al kill switch. |

## Segunda tanda (misma noche)

- **Permiso de ejecución:** la firma ahora incluye cantidad máxima y precio límite. El broker rechaza una orden con más cantidad o distinto precio que el autorizado. Con tests, incluido un permiso falsificado.
- **Loop de paper:** `src/shadow/str001_paper.py` conecta decisión → Risk Engine → router (emite el permiso) → PaperBroker, contra el precio ejecutable real, con liquidación en 0/1 al resolverse el mercado. Se activa con `--paper` (`run_shadow.bat` ya lo usa). 6 tests.
- **Limitación conocida:** las posiciones abiertas viven en memoria; si se reinicia el proceso, se pierde el estado de las abiertas (los logs JSONL quedan).
- **Sin probar en vivo:** todo lo que toca las APIs reales de Polymarket y Deribit.

## Cómo seguir

1. Reiniciar el recorder para que tome los cambios.
2. Correr `uv run python scripts/run_str001_shadow.py --once --paper`. Imprime cuántos mercados mapeó y por qué rechazó el resto, y es la primera prueba contra las APIs reales. Si anda, dejar `run_shadow.bat` corriendo.
3. Al cerrar los primeros mercados, correr `uv run python scripts/score_str001_shadow.py`. Mide qué tan bien calibrado está el valor justo de Deribit frente al mid de Polymarket, y el PnL hipotético por señal.

## Qué se corrigió desde la auditoría anterior

Lo verifiqué por muestreo leyendo el código y corriendo pruebas puntuales.

- **Risk Engine:** rechaza NaN, infinito y lados que no sean BUY/SELL, exige precio de marca y cuenta las órdenes en vuelo en el router.
- **Broker de paper:** exige un permiso firmado con HMAC, de un solo uso y con vencimiento.
- **Puerta de 24h/72h:** ahora mide el rango de tiempo de los datos y no el tiempo de reloj.
- **Holdout:** ahora se identifica por la huella del dataset, así que subir la versión ya no da otra mirada.
- **STR-002:** se arregló el ridge y se agregaron stop duro y sizing por riesgo. El event study entra al ask después de la latencia.
- **Recorders:** el sink ya no pierde filas (tiene cola de descarte), un manifiesto corrupto falla cerrado y Deribit ordena los vencimientos por fecha y vuelve a suscribirse.
- **API:** tiene token de operador para las mutaciones.

## Hallazgos

| # | Hallazgo | Dónde | Sev. | Verificado |
| --- | --- | --- | --- | --- |
| 1 | **No hay loop de paper.** `ExecutionRouter` y `on_market_event` solo se instancian en tests, y `paper_session_active` nunca pasa a True fuera de un test. Ninguna estrategia recibe datos en vivo, y el Risk Engine nunca recibe equity ni posiciones reales (`update_portfolio_state` no se llama en runtime) | `apps/api/services/data_service.py`, `src/execution_plane/router.py` | Bloqueante | Sí (grep de todo `src`, `apps` y `scripts`) |
| 2 | **STR-001 no tiene mapeo de mercados.** `generate_signal` espera `strike_price`, `time_to_expiry_years`, `deribit_forward_price`, `implied_volatility` y `dsigma_dK`, pero ningún módulo los construye. Falta distinguir "arriba de X en la fecha" (digital) de "toca X" (barrera, que vale cerca del doble). También falta conciliar la liquidación: Polymarket usa la vela de Binance de las 12:00 ET y Deribit el índice a las 08:00 UTC. El hurdle mezcla bps de nocional con unidades de probabilidad y no hay adaptador de Polymarket | `src/strategies/str001_empirical.py` | Bloqueante | Sí |
| 3 | **El libro de Polymarket casi no se graba.** Los eventos `book` solo llegan al suscribirse: hay 546 filas de L2 en unas 26 h para 974 tokens, y `price_change` se descarta. No hay profundidad para dimensionar ni para simular fills | `src/collectors/polymarket_recorder.py` | Crítico | Sí (reporte de aceptación) |
| 4 | **Probable orden invertido del libro de Polymarket.** El código toma `bids[0]` y `asks[0]` como el mejor precio, pero en el formato de Polymarket los bids vienen de menor a mayor, así que `bids[0]` es el peor. Si es así, el BBO derivado de `book` y el top-10 guardado son incorrectos. La tabla `best_bid_ask` no tiene este problema | `polymarket_recorder.py` | Crítico (por confirmar) | No. Los parquet están demasiado anidados para traerlos; la consulta para confirmarlo está más abajo |
| 5 | **El breaker de drawdown se puede saltar.** `is_risk_reducing` se calcula sin las órdenes en vuelo. Probé con drawdown del 20% y 1 BTC largo: el motor aprobó 5 ventas de 1 BTC, lo que deja -4 BTC (unas 4 veces el equity) con el breaker activo. Lo mismo pasa en el router, que registra en vuelo después de aprobar | `src/risk/engine.py` | Crítico | Sí (ejecutado) |
| 6 | **Broker de paper optimista.** (a) Un límite pasivo se llena sin ningún trade: cada actualización de BBO descuenta 1 unidad de la cola; probado, llenó después de 3 updates. Esto infla justo una estrategia maker en Polymarket. (b) No chequea el poder de compra: con USD 100 llenó 1000 BTC. (c) El PnL realizado excluye comisiones. (d) La firma del permiso no incluye cantidad ni precio | `src/paper/broker.py`, `authority.py` | Alto | Sí (ejecutado) |
| 7 | **Reloj del host.** El 99,7% de los eventos tienen edad negativa y el reloj de Windows va unos 4 a 6 s atrasado. La latencia "corregida" (p50 de unos 2 s) mezcla venues. Nada por debajo de 1 s es confiable: ni la puerta de latencia ni los 20 ms del broker | Host, `src/quality/metrics.py` | Alto | Sí (reporte) |
| 8 | **El reporte de calidad miente sobre símbolos.** Los símbolos se asignan a todas las venues que tienen una tabla con el mismo nombre: los "974 símbolos" de Binance y Deribit son hashes de Polymarket, así que `coverage_ratio` no sirve. `PEPEUSDT` no existe en futuros (es `1000PEPEUSDT`), así que nunca se graba. El poller de OI figura inactivo | `src/quality/metrics.py`, `config/settings.py` | Medio | Sí |
| 9 | **Descubrimiento de Polymarket sin filtro.** La segunda URL trae los 100 mercados top de cualquier categoría, y los tokens de mercados cerrados nunca se quitan. Se graban deportes y política en lugar de los mercados de umbral de BTC/ETH | `polymarket_recorder.py` | Medio | Sí (código) |
| 10 | **El recorder corre en la PC.** Hay huecos de horas completas (por ejemplo, la hora 22 del 3/10) y cada reinicio vuelve a empezar la puerta de 24h. Para un mes de paper hace falta una máquina que no se suspenda (un VPS) | Operación | Medio | Sí (listado de particiones) |
| 11 | **El DSR bloquea todo.** `var_sharpe` está fijo en 1,0. Con 20 intentos y un Sharpe por trade de 0,30 en 200 trades da DSR 0. La puerta va a rechazar cualquier estrategia, o alguien va a pasar `trial_count=1` para que pase | `src/portfolio/gates.py` | Medio | Sí (ejecutado) |
| 12 | `register()` acepta una estrategia directamente en PAPER o HOLDOUT si tiene tesis, salteando las puertas | `src/strategies/registry.py` | Medio | Sí (código) |
| 13 | `ExchangeAdapter.reconcile` importa `src.execution_plane.reconcile`, que no existe. `/health` devuelve HEALTHY como constante. El kill switch de la API exige un token que la UI no envía | `adapters/base.py`, `apps/api/main.py`, `apps/web/lib/api.ts` | Bajo | Sí |

## Consulta para confirmar el hallazgo 4

Desde la carpeta del proyecto, con DuckDB:

```sql
SELECT bids_price[1] AS b_first, bids_price[len(bids_price)] AS b_last,
       asks_price[1] AS a_first, asks_price[len(asks_price)] AS a_last
FROM read_parquet('data/raw/polymarket/table=orderbook_l2_depth/**/*.parquet')
WHERE len(bids_price) > 3 LIMIT 10;
```

Si `b_first` es menor que `b_last`, el orden está invertido y el mejor bid es el último elemento.

## Orden sugerido

1. **Recorders, ya mismo:** cada día grabado mal es historia perdida. Hay que corregir el orden del libro (4), grabar `price_change` o pedir snapshots periódicos (3), filtrar el descubrimiento a mercados de umbral de BTC/ETH (9), corregir `1000PEPEUSDT` y el reporte de símbolos (8), y sincronizar el reloj de Windows con `w32tm /resync` y NTP activo (7).
2. **Mapeo de STR-001 (2):** empezar con una sola familia, "BTC arriba de X en la fecha". Hay que parsear la pregunta y la regla de resolución, llevar T a la hora real de liquidación, interpolar la volatilidad en K desde las cadenas de Deribit y rechazar los mercados de barrera.
3. **Runner en modo sombra (1):** datos en vivo, estrategia y una señal registrada con su fair value, sin broker. Esto permite empezar a medir el edge de STR-001 mientras se arregla el resto, sin perder la ventana de un mes.
4. **Riesgo y broker (5 y 6):** contar las órdenes en vuelo en `is_risk_reducing`, exigir un trade al precio para los fills pasivos, chequear el cash y restar las comisiones del PnL. Después, conectar el router en modo PAPER al runner.
5. **Operación (10):** mover el recorder y el runner a un VPS antes de empezar el mes de paper.
6. **Gobernanza (11, 12, 13):** antes del primer holdout, no antes del paper.

**Tests negativos que faltan:** breaker con órdenes en vuelo; fill pasivo sin trades; compra sin cash; orden del libro de Polymarket con un fixture real; mapeo de un mercado de barrera, que debe rechazarse; y un test de integración del runner de punta a punta.

## Alcance

Leí completos el Risk Engine, el broker de paper, la autoridad de permisos, el router (camino de paper y de transmisión), el recorder de Polymarket, el manejo de mensajes de Deribit, STR-001, la agregación de calidad y la API (main, auth y paper). Revisé por muestreo gates, holdout, registry, allocator, capital pockets, STR-002 y el storage sink. Probé los hallazgos 5, 6 y 11 ejecutando código en una copia y corrí la suite completa. No pude abrir los parquet grabados porque superan la profundidad de carpetas que puedo traer, así que el hallazgo 4 queda por confirmar. Tampoco audité la UI más allá del cliente de la API.
