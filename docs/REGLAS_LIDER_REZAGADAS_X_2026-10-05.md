# Reglas de líder, rezagadas y X — 2026-10-05

## Estado

La variante de precio puro `leader -> laggard` permanece `REJECTED`. Las variantes con filtro de X siguen como hipótesis `RESEARCH`; este documento no promueve ni valida ninguna. No se habilitó capital live y no se cambiaron las reglas de entrada/salida del paper.

## Implementacion observada

En `src/paper/lider_paper.py`, la detección diaria usa velas completas de Binance. Un líder requiere retorno de 3 días de al menos +30% y volumen reciente de 3 días de al menos 2 veces el promedio previo de 30 días. La cesta requiere al menos cuatro miembros conocidos del segmento. Una rezagada tiene retorno de 3 días entre -10% y +5%, no es líder y se ordena por volumen; se toman hasta ocho. El mismo segmento tiene siete días de cooldown.

La rama `lider_x` consulta conversación de las últimas 48 horas y exige cinco publicaciones del activo más vínculo narrativo. `NO_DATA`, `API_ERROR`, `BUDGET_EXHAUSTED` y `NO_KEY` no equivalen a una señal negativa. El gasto X usa el ledger local compartido con Pump/X, con tope predeterminado de USD 1 por día. La consulta persiste modelo, versión, hash, estado, costo y request id seguro.

Cada cesta paper usa USD 1.000 por evento, horizonte de siete días y registro de costes/funding. Son parámetros del paper existente, no recomendaciones ni parámetros validados.

## Control

Se preserva el control histórico `lider_azar` como `UNMATCHED_CONTROL_V1`; sus resultados existentes no se reescriben. `MATCHED_CONTROL_V2` es un helper de investigación separado: matching causal con quote volume 30d, retorno previo de 3d y volatilidad; controles únicos y `NO_MATCH` cuando excede tolerancias o faltan datos. Tolerancias por defecto no fueron optimizadas y V2 no está integrado en la operativa ni tiene resultados de performance.

## Evidencia y límites

**NOT GENERATED — INSUFFICIENT EVIDENCE** para afirmar edge neto, significancia, estabilidad por régimen o ventaja del filtro X. Los tests verifican causalidad, retry/idempotencia y matching, no rentabilidad. La pantalla paper es evidencia operativa, no un holdout independiente. Antes de una conclusión hace falta un periodo prospectivo suficiente, costes completos y comparación emparejada preespecificada.

## Cambios de integridad del batch

El checkpoint diario queda `STARTED` y solo se completa después de persistir el resultado; los errores permanecen `FAILED_RETRYABLE`. Se agregó V2 sin alterar el V1. El panel muestra salud del proceso separada de ausencia de eventos.
