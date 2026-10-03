# Auditoría del backend — Trading / Quant OS

3 de octubre de 2026

El backend está completo en estructura, pero varias garantías clave (veto del Risk Engine, gates a prueba de fallos, holdout sellado) solo se cumplen dentro de los tests y no en los caminos reales de código; hay que corregir los puntos críticos antes de empezar el paper.

## Críticos y altos

Hoy no hay riesgo real, porque el capital live está bloqueado y la API solo tiene endpoints GET, pero estos puntos invalidan resultados o dejan caer una protección justo cuando empecemos paper y examen. Los dos primeros bloques (riesgo y datos) son los más urgentes.

| # | Hallazgo | Dónde | Sev. | Arreglo |
| --- | --- | --- | --- | --- |
| 1 | El Risk Engine no está en el camino de las órdenes: `evaluate_order` solo se llama desde tests y `PaperBroker.submit_order` acepta cualquier orden. El bloqueo de capital depende de que quien llama pase `is_live=True` | `paper/broker.py`, `risk/engine.py` | Crítico | El broker exige un token de aprobación del Risk Engine; el bloqueo pasa a ser una constante de proceso |
| 2 | Con NaN el Risk Engine aprueba: equity NaN y 1000 BTC de compra dio APPROVED; el lado "HOLD" se trata como venta | `risk/engine.py` | Crítico | Rechazar todo valor no finito, lista blanca BUY/SELL, equity mayor que 0 |
| 3 | La puerta de 24h/72h da PASS con casi nada de datos: usa tiempo de reloj, no el de los datos. Con 10 filas de un símbolo, PID muerto y manifiesto de 80 h dio `CHECKPOINT_72H_PASS` | `quality/reporter.py`, `acceptance.py`, `data_service.py` | Crítico | Medir el rango de tiempo de los datos por venue, huecos máximos, cobertura mínima y proceso vivo |
| 4 | El holdout es un registro, no un sello: la clave es (estrategia, versión), así que subir a 1.0.1 da otra mirada; no valida la huella de parámetros ni bloquea mirar los datos antes | `research/holdout.py` | Crítico | Huella de parámetros pre-registrada, clave por hash del dataset, el manager carga los datos con lock |
| 5 | El modelo de residuo de STR-002 v2 está roto: con ridge 0,01 una beta real de 1,5 se estimó en 0,07, así que casi no se quita BTC; además el ajuste incluye la barra del shock | `strategies/str002_v2.py` | Crítico | Escalar el ridge, o usar OLS/Huber, y ajustar en una ventana que termine antes del shock |
| 6 | STR-002 v2 no tiene stop duro ni sizing por riesgo, y el "primer reversal" pasa 89,6% de las veces con ruido puro | `strategies/str002_v2.py` | Alto | Implementar stop, `risk_budget/(stop+slippage)` y una máquina de estados del shock |
| 7 | El event study es clarividente: el retorno es la mejor salida con visión retrospectiva, sin cruzar spread; tier, spread y profundidad están hardcodeados; el umbral de 8 bps está bajo el costo de ida y vuelta de 10 bps | `strategies/str002_event_study.py`, `backtest/engine.py` | Alto | Horizontes por tiempo, entrada al ask tras latencia, datos PIT reales |
| 8 | La API muestra conciliación "SYNCHRONIZED, cero drift" como texto fijo, aunque nunca corre; los kill switches por ámbito se devuelven fijos como ARMED | `routers/execution.py`, `data_service.py` | Crítico | Devolver `NOT_RUN`/`UNKNOWN` hasta que un reconciliador real escriba un resultado |
| 9 | El estado del kill switch ignora el ámbito: GLOBAL activado y luego un RESET de ASSET devuelve RESET; el global vive en memoria y un reinicio lo borra | `persistence/domain.py` | Alto | Estado por ámbito, carga desde el store al arrancar, UNKNOWN sin eventos |
| 10 | Exposición subestimada: órdenes en vuelo no cuentan (10 órdenes de 24k pasaron un tope de 25k) y una posición sin precio de marca cuenta como 0 | `risk/engine.py`, `event_cluster.py`, `capital_pockets.py` | Alto | Contar órdenes pendientes y rechazar si falta marca vigente |
| 11 | El agregador neta posiciones opuestas entre cuentas (+600k BTC propio y -600k en prop pasa con 100k de equity); el drawdown global y el pocket congelado no se aplican | `risk/capital_pockets.py` | Alto | Sumar bruto por cuenta, aplicar drawdown global y estado congelado |
| 12 | `all_gates_pass([un solo PASS])` da True; DSR con NaN da PASS; Gate D con series vacías da PASS; Gate B pasa 19% de series de puro ruido con n=60 | `portfolio/gates.py` | Alto | Exigir A, B, C y D de la misma versión y dataset; PENDING si faltan datos; mínimos de muestra |
| 13 | DSR mal alimentado: varianza entre pruebas fija en 1,0, mezcla de Sharpe anualizado con fórmula por período, `trial_count` lo pasa quien llama; FDR de Benjamini-Hochberg se anuncia pero no está implementado | `portfolio/gates.py`, `backtest/validation.py` | Alto | Sharpe por período, varianza de los intentos registrados, conteo anclado al registro |
| 14 | Los recorders pierden datos sin avisar: el buffer se vacía antes de escribir, sin contador ni cola de errores; no hay marcas de desconexión ni ids de secuencia del libro; un manifiesto corrupto se reinicia en vacío | `common/storage_sink.py`, `collectors/*`, `common/manifest.py` | Alto | Reencolar o archivo de descarte con contador, tabla `feed_events`, fallar cerrado ante manifiesto corrupto |
| 15 | Posibles errores en lo que ya se está grabando: Deribit ordena vencimientos como texto (`1OCT26 < 26DEC25`) y no resuscribe; Polymarket toma 100 tokens arbitrarios sin resuscribir y trata `price_change` como trades con precio 0 | `collectors/deribit_recorder.py`, `polymarket_recorder.py` | Alto (por confirmar) | Revisar ya el contenido de los 4,9M de filas |
| 16 | Allocator: un multiplicador de régimen de 5,0 da 200k sobre un tope de 40k; si todas las estrategias son carreras de latencia reparte pesos iguales; métricas faltantes se asumen en el mejor caso | `portfolio/allocator.py` | Alto | Limitar multiplicadores a [0,1], asignar 0 sin pesos, peor caso por defecto |
| 17 | El ciclo de vida se puede saltar: `register()` acepta PAPER, HOLDOUT, etc., sin evidencia; la única barrera es un booleano que la propia estrategia pone, y no está conectado a `gates.py` | `strategies/registry.py`, `models.py` | Alto | `register()` solo en IDEA o RESEARCH; `update_stage` exige bundle de gates verificado |
| 18 | Monte Carlo del examen mal modelado: `daily_loss_mode` y `resampling_mode` no se leen (resultados idénticos), el MAE se divide por una constante, la regla de consistencia usa 0,35 y no 0,30, sin intervalo de confianza, y el límite de 5 intentos se reinicia cambiando la versión | `risk/capital_pockets.py` | Alto | Implementar ambos modos, MAE relativo a la cuenta, persistir el contador |
| 19 | Supabase: `list()` sin paginar (con tope de 1000 filas por defecto, no probado) puede hacer que el kill switch, el conteo de intentos y la cadena de auditoría vean solo las filas más viejas; la escritura inmutable tiene una carrera que puede marcar como sincronizado un dato distinto | `persistence/supabase_backend.py` | Alto | Paginar; comparar el payload devuelto en conflicto |
| 20 | API sin autenticación ni límite de conexiones; el SSE es un bucle infinito por cliente que bloquea el event loop; hay fugas de rutas, autores de commits y `str(e)` | `main.py`, `routers/stream.py`, `routers/system.py` | Alto | Clave de API global, tope de conexiones SSE, errores genéricos |

## Medios y bajos

- **Migración SQL:** la seguridad de filas (RLS) está activa en las 30 tablas y sin políticas para `anon`, lo cual está bien. Falta un trigger contra `TRUNCATE` en las tablas inmutables, `CHECK (authorized_live_capital_usd = 0)`, índices únicos en `idempotency_key` y `seq`, y revocar la ejecución pública de `forbid_mutation()`. El bloqueo de USD 0 hoy existe solo en Python.
- **Cadena de auditoría:** con dos escrituras concurrentes se bifurca (confirmado), y el `/api/audit` es una lista en memoria que se pierde al reiniciar.
- **Paper y riesgo:** `record_order` puede pasar de FILLED a NEW; `bool("false")` da True; el `equity_usd` y el PnL no realizado están fijos y una compra ejecutada aparece como pérdida.
- **Estados fijos:** `/health` devuelve "HEALTHY" y "$0 (LOCKED)" como constantes; `QUANT_OS_MOCK_MODE=1` no tiene guarda de producción.
- **Replicación:** verifica por tamaño y no por hash; un objeto distinto del mismo tamaño queda como sincronizado; acepta `http://` y mandaría la clave de servicio.
- **Broker de paper optimista:** los fills pasivos ignoran el volumen y el lado del trade, no hay chequeo de poder de compra (100k comprados con 100 en caja), el PnL realizado excluye comisiones y la cancelación tiene latencia cero.
- **Backtest:** una orden a mercado llena todo al mejor precio más 1 bp, sin consumir profundidad; `cost_basis` no se reduce tras ventas parciales y puntuó dos rondas ganadoras como una ganadora y una perdedora; Sharpe anualizado como si las barras fueran minutos.
- **Ejecución:** `dry_run` acepta False, y la clave de idempotencia incluye un bucket de 10 s, así que un reintento a los 10 s genera otra clave.
- **Atribución y régimen:** con volatilidad NaN el régimen sale NORMAL, los trades duplicados se cuentan dos veces y el contador de ganadas/perdidas está inventado.
- **Gate de evidencia multicuenta:** no verifica que la evidencia corresponda al proveedor y la cuenta, y distingue mayúsculas ("ftmo" y "FTMO " cuentan como cuentas distintas).
- **Calidad de datos:** la consulta agrupa por `venue` en tablas que no tienen esa columna, falla y el `except` lo oculta, así que `binance_oi_active` salió False con datos presentes; las latencias corregidas tienen pisos de 5/10/20 ms.
- **Loader PIT:** el `symbol` se interpola en SQL y `stream_events_as_of` falla con tablas de trades y profundidad.
- **Resto:** el parche de DNS fija dos IPs de Cloudflare que quedarán viejas (no debilita TLS); el poller de OI ignora `Retry-After`; la probabilidad digital no se recorta a [0,1]; la entrada de STR-001 mezcla bps de comisión con unidades de probabilidad; el CI no declara `permissions:` y `pytest` está en dependencias de runtime.

## Orden de corrección antes del paper

1. **Datos que ya se están grabando (hallazgos 14 y 15):** revisar qué contienen realmente los 4,9M de filas de Polymarket y Deribit. Si el parseo es el de los hallazgos, hay que corregir los recorders cuanto antes, porque cada día grabado mal es historia perdida para STR-001.
2. **Seguridad del riesgo (1, 2, 10, 11):** meter el Risk Engine en el camino del broker, validar valores finitos y contar órdenes en vuelo.
3. **Verdad de la API (3, 8, 9):** reemplazar valores fijos por `UNKNOWN`/`NOT_RUN` y derivar el estado de las puertas de los datos.
4. **Validez de STR-002 (5, 6, 7):** arreglar el residuo y el event study antes de correr el backtest, porque con estos errores los resultados saldrían inflados y no sirven para decidir el examen.
5. **Gates y holdout (4, 12, 13, 17):** exigir A a D completos y sellar el holdout antes del primer holdout real.
6. **Persistencia y API (19, 20 y migración):** paginación, autenticación, TRUNCATE y CHECK de capital.
7. **Monte Carlo y allocator (16, 18):** antes de comprar cualquier examen.

Mi estimación es que los puntos 1 a 5 son trabajo de unos pocos días para Codex en modo plan, pero es una estimación y no una medición.

**Tests negativos que faltan:** NaN, infinito, lado desconocido, equity cero y marca ausente en el Risk Engine; Risk Engine junto con el broker; `dry_run=False` rechazado; PASS falsificado, DSR con NaN, Gate D vacío y `all_gates_pass` con un conjunto parcial; saltar etapas en el registro; multiplicador de régimen mayor que 1; congelado y drawdown global en el agregador; gate 24h/72h con datos escasos; holdout reutilizado con versión nueva; y pruebas reales de `SupabasePersistenceBackend` (hoy el "remoto" es una subclase de SQLite). Varios tests actuales afirman los valores fijos o aceptan los dos resultados posibles, así que pasan aunque el comportamiento sea el incorrecto.

## Lo que está bien hecho y alcance

**Bien hecho:**

- La migración se genera desde una sola fuente con un test de deriva, con RLS en las 30 tablas.
- Hay un libro local con cola de salida idempotente, y `NotConfiguredError` no gasta reintentos.
- La clave de Supabase no se filtra en `repr` ni en `status()`, y `.env.example` solo tiene marcadores.
- La API en modo normal no inventa números: atribución, mercados, prop y backtests devuelven `NOT_AVAILABLE`.
- `CapitalPocketStore` rechaza autorización distinta de cero; el perfil de prop no permite VERIFIED ficticio; el perfil nuevo arranca en UNKNOWN y falla cerrado.
- ARCHIVED es terminal, los modelos son inmutables y `extra=forbid`.
- La carga PIT usa hora de recepción y las partes se escriben con renombrado atómico.
- Las fórmulas de Black-76, la derivada de probabilidad digital, DSR, Holm y BH son estándar; el fallo es lo que se les pasa como entrada.

**Alcance:** tres revisores leyeron por completo `apps/api`, `src/persistence`, la migración, `src/risk`, `src/execution`, `src/paper`, `src/portfolio`, `src/strategies` (registry, models, str002_v2 y los otros), `src/collectors`, `src/quality`, `src/research`, `src/backtest`, `src/quant`, `src/common`, `scripts` y los tests clave. La mayoría de los hallazgos se confirmaron ejecutando fragmentos de código sobre una copia; los marcados "por confirmar" o "plausible" no se verificaron. Yo no volví a ejecutarlos por mi cuenta. No se auditaron la carpeta `apps/web` (la UI) ni los datos grabados, ni se corrió la suite completa de tests.
