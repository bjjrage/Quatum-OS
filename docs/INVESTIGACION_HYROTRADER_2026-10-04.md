# Investigación Binance → HyroTrader — 4 de octubre de 2026

**Cuenta de referencia: Two-Step, USD 10.000. Resultado: ninguna estrategia probada con suficiente evidencia para asignarle capital.** Hay dos hipótesis de flujo con resultados históricos interesantes, pero la corrección por pruebas múltiples, la dependencia del calendario y la falta de validación en Bybit impiden declararlas un edge confirmado.

Se probaron 42 configuraciones nuevas de nueve familias. Se añadieron ocho casos de ejecución/protección, doce calendarios adicionales y dos agregaciones de calendarios: 64 pruebas nuevas contabilizadas. Sumadas a 210 configuraciones conocidas de investigaciones anteriores, el conteo conocido es al menos 274; no incluye todos los experimentos antiguos de replay y PYR. Ningún candidato pasa siquiera el filtro estadístico inicial de 252 pruebas, y ampliarlo a 274 tampoco produce un aprobado. No se modificaron el registro de estrategias ni la asignación de capital.

## Git y datos locales

Al comenzar, el árbol estaba limpio y `HEAD`, `origin/main` y la referencia consultada directamente en GitHub coincidían en `fb778314636e64d20ba6a22699481201916f4f3c`, repositorio `bjjrage/Quatum-OS`. **El código existente sí estaba pusheado.** El histórico y los resultados de investigación están excluidos por `.gitignore`: no están respaldados en GitHub.

Esta investigación agrega código, pruebas y este informe en local. Durante el trabajo aparecieron cambios paralelos en `apps/api/main.py` y `apps/api/routers/research_spot.py`; se conservaron intactos y no se incluyeron en ninguna publicación. No se creó un commit ni se hizo push.

| Conjunto | Cobertura / volumen |
|---|---|
| Histórico Binance USD-M | 1.000,3 MiB; 65 contratos |
| Velas de 1 minuto | 23.961.600 filas; 2025-10-01 a 2026-10-03, cobertura desigual por contrato |
| Velas de 1 hora usadas | 2.100.975 filas; 2021-10-05 a 2026-10-03 |
| Funding usado | 362.418 eventos |
| Recorder de varios venues | Aproximadamente 3.246 MiB; pocos días de captura, insuficientes para probar microestructura a través de regímenes |

La cobertura común de minutos para todos los activos seleccionados comienza en abril de 2026. El intento de comenzar la ejecución detallada en octubre de 2025 se detuvo al encontrar precios faltantes; no se rellenaron ni se descartó ese activo para fabricar una muestra completa.

La auditoría completa encontró cero minutos duplicados, cero velas inválidas y cero eventos duplicados de funding. En 399,360 horas comparables hubo 273 diferencias entre el OHLC horario y su agregación desde minutos: todas comenzaron con un minuto sin volumen, que puede conservar el precio previo. La diferencia máxima fue 0,93%. Se conservan ambos orígenes y se reporta la discrepancia.

Hay 64,976 eventos cuyo mark price es NaN o no positivo. Para valorar el funding se usó el precio contemporáneo de la vela, una aproximación explícita al mark. No faltaron eventos de funding en días completos de velas; el mayor intervalo entre eventos fue de aproximadamente ocho horas. Esto comprueba consistencia interna, no reemplaza datos de ejecución de Bybit ni elimina el sesgo de supervivencia del universo seleccionado.

## Reglas usadas y su consecuencia

La tabla oficial para Two-Step indica objetivo del 10% y luego 5%, pérdida total fija del 10% y pérdida diaria del 5%. La FAQ vigente define el piso diario como equity a las 00:00 UTC menos el 5% del capital inicial, incluyendo flotantes y comisiones. En una cuenta de USD 10.000 son USD 1.000 de objetivo inicial, USD 500 de verificación y USD 500 de presupuesto diario. Las 00:00 UTC son las 21:00 de Paraguay. [Tabla oficial](https://www.hyrotrader.com/trading-rules/), [cálculo diario](https://www.hyrotrader.com/faq/rules/how-is-the-5-daily-drawdown-calculated/).

Un día válido requiere cerrar al menos una operación cuyo tamaño sea ≥5% del capital inicial y cuyo movimiento bruto sea ≥1% de su propio valor. Son cinco días válidos por fase. Para USD 10.000, una operación de USD 100 no cumple; una de USD 625 puede cumplir si se mueve al menos 1%. La ganancia que cuenta por día está limitada al 40% del objetivo: USD 400 en Challenge y USD 200 en Verification; las pérdidas cuentan completas. [Días válidos](https://www.hyrotrader.com/faq/evaluation-process/minimum-trading-days/), [distribución de ganancias](https://www.hyrotrader.com/faq/rules/what-are-the-risk-management-conditions-at-hyrotrader/).

En funded, el nominal agregado tiene límite de 2× el capital inicial y el margen de 25%. Los activos low-cap tienen un límite conjunto de exposición del 5% inicial incluyendo apalancamiento. **No tenemos capitalizaciones históricas ni clasificación de Innovation Zone para certificar este requisito.** Volumen alto no demuestra que un activo sea elegible. [Límites funded](https://www.hyrotrader.com/faq/rules/are-there-any-other-rules-for-a-funded-account/), [riesgo low-cap](https://www.hyrotrader.com/faq/rules/what-are-the-risk-management-conditions-at-hyrotrader/).

Se comprobó además el umbral publicado de 3% de pérdida realizada por posición. Un artículo oficial de septiembre describe otras reglas —drawdown trailing y 6% total incluso para Two-Step— que contradicen la tabla y FAQ actuales. Se guardó una captura de la configuración embebida de la tabla y se corrió ese escenario más estricto como sensibilidad. Para ejecutar habría que vincular el perfil al contrato/dashboard de la cuenta concreta. [Pérdida por posición](https://www.hyrotrader.com/faq/rules/what-is-the-maximum-loss-per-trade-rule/), [artículo contradictorio](https://www.hyrotrader.com/blog/prop-firm-pass-rates/).

## Método y respaldo de las hipótesis

Entrenamiento: marzo de 2022 a diciembre de 2023; validación: 2024; prueba retrospectiva: 2025–2026. Se purga el horizonte completo más dos días antes de cada frontera. La elección usa el menor Sharpe entre entrenamiento y 2024. **2025–2026 ya había sido observado por laboratorios anteriores: no es un holdout virgen.** Se calcularon errores Newey-West con siete rezagos y corrección Bonferroni. También se usaron 5.000 remuestreos en bloques de siete días, con semilla fija; esos intervalos son exploratorios y no corrigen la selección previa.

Las señales usan datos cerrados. La ejecución es a las 01:00 UTC del día siguiente, con una hora de demora. Se mantienen cantidades fijas y se cobra cada cierre y reapertura, incluyendo el nominal de salida y funding. Se usa sizing respecto del capital inicial, sin compounding. Los retornos largos son cambios del equity marcado; la prueba de minutos liquida también las posiciones finales.

Coste base: 5,5 bps de taker y 2 bps de deslizamiento por lado, 15 bps ida/vuelta. Stress: 25 bps ida/vuelta. Es una hipótesis de coste con referencia en la tarifa publicada por Bybit; falta verificar las tarifas específicas del challenge y de cada contrato. [Tarifa oficial de referencia](https://www.bybit.com/en/help-center/article/FAQ-USDT-Perpetual-and-Expiry-Contracts).

Se probaron flujo comprador, flujo residual, aceleración del flujo, momentum relativo, tendencia, breakout, reversión, reversión con bajo volumen relativo y funding. Momentum tiene antecedentes publicados, pero ese resultado académico no garantiza rentabilidad en estos perpetuos. El estudio reciente sobre order flow usa flujos internacionales de once monedas; nuestro indicador de takers de un único exchange es un proxy diferente, no una reproducción de ese estudio. [Factores cripto](https://www.nber.org/papers/w25882), [momentum temporal](https://www.nber.org/papers/w24877), [order flow](https://doi.org/10.1016/j.finmar.2026.101047).

## Lo que sí apareció

Universo dinámico: los 20 contratos más líquidos del universo local según volumen de 28 días, con ≥90 días completos y ≥USD 5 millones diarios. El flujo es `2 × volumen comprador agresivo / volumen total − 1` acumulado durante siete días. Se compra el 20% superior y vende el inferior, con pesos iguales y rebalanceo semanal. El candidato residual elimina mediante regresión transversal la parte del flujo explicada por el retorno reciente antes de ordenar los activos.

| Candidato | Sharpe train | Sharpe 2024 | Sharpe 2025–26 | Neto 2025–26, exposición 1× | Caída máxima vs capital inicial |
|---|---:|---:|---:|---:|---:|
| flow_7d_r7_liquid20 | 1,60 | 2,47 | 1,25 | 56,80% | 18,29% |
| flow_residual_7d_r7_liquid20 | 1,35 | 1,84 | 1,64 | 67,08% | 21,17% |
| funding_7d_r7_liquid20 | 1,07 | 2,70 | 1,23 | 70,64% | 47,75% |

Son 639 intervalos en el último tramo. Los retornos son acumulados aritméticos sobre capital inicial; no son CAGR ni expectativas de beneficio futuro. Con costes de stress, el flujo simple suma 47,77% y el residual 58,05%. Eso es atractivo como hipótesis, pero sus p-values corregidos de entrenamiento son 1,00. El carry pierde fuerza al separar años y tiene una caída muy grande para PROP.

El calendario es una falsificación importante. Los siete Sharpe del flujo simple son 1,25; −0,07; −0,02; −0,11; 1,03; 1,07; 1,17. Para el residual: 1,64; 0,49; 0,43; −0,03; −0,68; −0,15; 0,69. **No corresponde elegir ahora el día ganador.** Los resultados originales de cada calendario quedaron guardados.

## Ejecución de minutos y protección

Periodo común y calendario original: 5 de abril a 3 de octubre de 2026, 182 días. Exposición total inicial de USD 5.000: aproximadamente USD 625 por pata en una cartera de ocho activos. Protección predefinida: stop a 8% de distancia de precio y circuito de cartera al perder 1,5% del capital inicial en el día UTC. Tras cerrar por riesgo, se espera al siguiente rebalanceo. Un stop con gap se ejecuta al precio de apertura peor; el circuito liquida a extremos adversos de la vela de un minuto, con todos los costes. El 1,5% es un disparador, no una garantía del fill.

| Señal | Versión | Neto acumulado sobre USD 10.000 | Caída máxima acumulada | Peor día UTC | Sharpe |
|---|---|---:|---:|---:|---:|
| Flujo comprador | Sin stops | 3,86% | 8,18% | -2,77% | 0,54 |
| Flujo comprador | Protegida | 2,32% | 6,97% | -2,15% | 0,45 |
| Flujo ajustado | Sin stops | 7,02% | 10,17% | -2,92% | 0,98 |
| Flujo ajustado | Protegida | 6,74% | 4,17% | -1,57% | 1,43 |

La versión residual protegida cerró 59 veces por stop de posición y una por circuito diario. Su mayor pérdida realizada por operación fue 0,54% del capital inicial. Ganó aproximadamente USD 674, con caída máxima de USD 417; **en esta ventana no alcanza ni el primer objetivo del 10%**. La media diaria tiene un intervalo de confianza que incluye cero. No se anualiza esta ventana para vender una expectativa.

En el replay horario sin protección hubo diez fechas de inicio, separadas por 28 días y con hasta 360 días por intento. Se reinician cuenta y posiciones al pasar a Verification; se mantienen el calendario original, ganancias realizadas, límites diarios y días válidos. Los extremos horarios de varias patas pueden no ser simultáneos y producen un límite adverso conservador.

| Candidato, exposición 0,5× | Casos que completan numéricamente ambas fases bajo FAQ actual |
|---|---:|
| flow_7d_r7_liquid20 | 0 / 10 |
| flow_residual_7d_r7_liquid20 | 1 / 10 |
| funding_7d_r7_liquid20 | 1 / 10 |

Estos casos se solapan y **no representan una probabilidad de aprobación**. Tampoco incluyen la aprobación manual ni certificación low-cap/Bybit. Los casos fallidos por una posición de más de 3% muestran por qué un buen retorno agregado no basta.

## Una mejora creativa que también se midió

Para evitar seleccionar el mejor día, se promedió la exposición de siete cohortes, una por calendario semanal, con una séptima parte del presupuesto cada una. Se conservan sus costes completos sin atribuir ahorros hipotéticos por neteo.

| Ensamble, exposición 0,5× | Sharpe train | Sharpe 2024 | Sharpe 2025–26 | Neto 2025–26 | Caída máxima |
|---|---:|---:|---:|---:|---:|
| flow_7d_r7_liquid20 | 0,71 | 1,82 | 0,75 | 15,25% | 8,27% |
| flow_residual_7d_r7_liquid20 | 0,50 | 2,34 | 0,38 | 6,60% | 8,51% |

Es una agregación exploratoria después de observar la sensibilidad, no una nueva estrategia validada. Las salidas de cada cohorte pueden quedar por debajo de USD 500 y no sumar días válidos del challenge. Todavía no tiene replay de stops ni contabilidad de posiciones agregadas según la plataforma. Su utilidad potencial para operar funded y su capacidad para aprobar una evaluación son cuestiones distintas.

## Decisión y siguiente evidencia necesaria

Mantener **flujo comprador semanal** y **flujo residual protegido** en investigación. Descartar por ahora las versiones de tendencia/reversión de esta búsqueda y el carry como solución de challenge. Ninguna recibe capital ni se conecta a un exchange.

Antes de llevar un candidato al paper operativo: congelar una sola configuración y calendario; obtener elegibilidad y precios/funding de Bybit punto en el tiempo; excluir todo activo de clasificación desconocida; y repetir el resultado con tarifas y fills del entorno concreto. Una restricción a grandes activos ya debilitó la señal en esta búsqueda, por lo que no se puede sustituir silenciosamente el universo y conservar las métricas de altcoins.

El paper nuevo debería medir costes, latencia, slippage, correlación de patas, riesgo diario, días válidos y distribución de ganancias. Doce semanas y cien cierres pueden servir como control inicial de ejecución, pero no demostrar por sí solas alpha estadístico. Para reclamar edge se necesita evidencia nueva, estabilidad de parámetros/calendario y confianza estadística después de contar todos los ensayos. Aprobar ocasionalmente un recorrido histórico no sustituye esa evidencia.

## Reproducción y archivos

Se agregaron módulos aislados de investigación, tres ejecutores, una auditoría y un generador de informe. Pasaron **21 pruebas**: financiación al nominal marcado, costes de entrada/salida, cantidades fijas, ausencia de look-ahead, datos faltantes, riesgo flotante, calendario, mínimos de operación, fills con gap y conciliación de cash; también los laboratorios existentes seleccionados.

```powershell
.venv/Scripts/python.exe scripts/audit_hyro_inputs.py
.venv/Scripts/python.exe scripts/research_hyro_edges.py
.venv/Scripts/python.exe scripts/research_hyro_minute.py
.venv/Scripts/python.exe scripts/stress_hyro_edges.py
.venv/Scripts/python.exe scripts/write_hyro_report.py
.venv/Scripts/python.exe -m pytest tests/test_hyro_edge_research.py tests/test_strategy_lab.py tests/test_portfolio_lab.py -q -p no:cacheprovider --basetemp .tmp/hyro-new-check
```

Evidencia completa en `data/research/hyro_2026_10_04/`: protocolos, fingerprint SHA-256 de los archivos horarios/funding, auditoría, las 42 filas en JSON/CSV, operaciones y equity de minutos, stress de calendario, resultados del challenge y captura de reglas oficiales. La carpeta `minute_coverage_anchor_sensitivity` conserva la prueba inicial con otro anclaje de cobertura; no se usa como resultado principal. El fingerprint identifica los archivos locales y no certifica por sí solo su origen.
