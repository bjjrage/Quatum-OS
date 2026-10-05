# STR-002 y laboratorio — resultados disponibles al 2026-10-05

Este documento resume únicamente artefactos de research ya guardados localmente. No se ejecutó Strategy Sweep 02 ni se regeneraron históricos durante el batch. Ningún resultado cambia el estado de una estrategia.

## STR-002 replay guardado

`data/research/str002_replay_latest.json` cubre aproximadamente 1,73 días grabados y 23 alts; hay 2.490 minutos usables, 200 minutos sin recorder y un tramo continuo máximo de 5,98 horas. Todas las variantes tienen menos de 30 operaciones: A 1, B 11, C 3 y D 3. Los resultados netos por trade guardados son negativos (aprox. -0,23% a -0,37%) y el control al azar figura `IGUAL_QUE_AZAR` para B y D. El propio archivo advierte que el tamaño de muestra es demasiado bajo para concluir.

Conclusión: STR-002 no demuestra edge económico ni aprobación de un examen. Su estado sigue sin validar.

## Laboratorios diarios guardados

- `strategy_lab_latest.json`: 150 ideas, 65 criptos, 254,9 días de entrenamiento y 109,25 días de prueba final; la lista `pasan` está vacía y ninguna familia tiene ideas aprobadas.
- `portfolio_lab_latest.json`: 41 estrategias, 65 criptos, periodo 2022-03-05 a 2026-10-03, 1.171 días de entrenamiento y 502 de prueba; `pasan` está vacío.
- `recorder_studies_latest.json`: 47,83 horas y 25 símbolos; 33 eventos BTC y 62 mercados Polymarket usados. Las 29–31 apuestas guardadas por umbral muestran retorno medio antes de costes de aproximadamente -4,9% a -7,9% por dólar. El artefacto precede a la corrección de economics/provenance, así que no es una estimación neta actual.

Estos resultados son pequeños o retrospectivos y no prueban persistencia fuera de muestra.

## Simulador Hyro

`exam_sim_latest.json` es anterior al guard de reglas de este batch y guarda probabilidades `pasa_pct` bajo una formulación anterior. **No usar esas cifras para elegir una estrategia, comprar una Challenge ni afirmar PASS/FAIL.** El código actualizado marca `RULES_UNVERIFIED`, versiona la fuente y devuelve únicamente proyecciones `*_MODEL_ONLY`; falta conocer el modo de drawdown de la cuenta y faltan inputs intradía/trade-level. La referencia del usuario es la Challenge de dos fases con cuenta de USD 10.000, pero estos artefactos no evalúan esa cuenta de forma autoritativa.

Reglas oficiales consultadas el 2026-10-05: [etapas y objetivos](https://www.hyrotrader.com/faq/getting-started/how-to-start/), [días mínimos válidos](https://www.hyrotrader.com/faq/evaluation-process/minimum-trading-days/), [drawdown diario](https://www.hyrotrader.com/faq/rules/how-is-the-5-daily-drawdown-calculated/) y [modos de drawdown](https://www.hyrotrader.com/faq/rules/what-is-the-difference-between-standard-trailing-and-swing-fixed-daily-drawdown/). La diferencia de modo de cuenta impide fijar una aprobación universal: el estado se mantiene `RULES_UNVERIFIED`.

## Decisión de investigación

**NOT GENERATED — INSUFFICIENT EVIDENCE** para llamar ganadora a STR-002 o a cualquier idea del laboratorio. No se cambió registry, etapa, umbral o promoción. La siguiente investigación requiere datos íntegros, fees/provenance completos, muestra prospectiva y control/holdout preespecificados.
