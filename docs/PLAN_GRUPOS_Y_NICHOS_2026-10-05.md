# Plan de grupos y nichos Pump.fun — 2026-10-05

## Estado

`PAPER / RESEARCH ONLY`. No se cambió la estrategia Pump.fun, no se promovió su estado y no se habilitó live execution. No se ejecutó un nuevo sweep.

## Implementacion observada

`src/paper/pump_paper.py` mantiene cuentas paper para señales de grupos coordinados, una variante de aguantar, un control azar y señales por nicho caliente. La alimentacion y el precalentamiento leen eventos de Pump.fun; la UI separa grupos detectados, cuentas, cierres, comisiones y salud del proceso. El inventario local contiene `pumpfun_trades` de 2026-10-05 00–21 UTC: 2.567.859 filas declaradas por manifests en 770 archivos, 353,2 MiB. El estimador de duplicados de la muestra no encontró filas exactamente idénticas en 67.383 filas muestreadas; esto no prueba unicidad global.

El resultado local guardado `data/research/pumpfun_intel_latest.json` informa 29.082 operaciones de eventos, 946 tokens, 42 grupos y 534 pares coordinados en aproximadamente 0,15 horas; la sección de habilidad de billeteras figura `POCOS_DATOS`. Se reporta como artefacto exploratorio guardado, no como backtest neto ni evidencia de edge.

## Modelo de costos

El paper todavía aplica `FEE = 1,25%` por lado. Se versionó como `PUMPFUN_FEE_SCHEDULE_2026-05`, verificado el 2026-10-05 contra la [documentación oficial de tarifas](https://pump.fun/docs/fees), pero el modelo completo queda `ECONOMICS_UNVERIFIED`: la tarifa depende de la ruta/estado del mercado y los tiers de PumpSwap graduado no quedan representados por la comisión fija del paper. La lógica de entradas y salidas permanece intacta.

## Pendiente

**NOT GENERATED — INSUFFICIENT EVIDENCE** para validar rendimiento después de todos los costos, slippage de ejecución y sesgo de supervivencia. La muestra local breve y el estado `POCOS_DATOS` impiden recomendar capital real. El `azar` existente no se reemplazó; cualquier estudio nuevo debe fijar de antemano universo, fees/ruta, criterios y holdout.
