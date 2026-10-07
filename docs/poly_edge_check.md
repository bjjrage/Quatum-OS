# Polymarket up/down vs Binance: ¿es operable?

2025 mercados dentro del período. Fee por mercado según su `fee_schedule` grabado (`acciones × p × rate × (p(1−p))^exp`). Neto = después de fee. Precio = ask (o 1−bid) del bucket de 5 s posterior al retraso.

## Retraso de ejecución 5 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 482 | +0.077 | +19.1% | 0.0058 | 49% | 3.6 | 2.2 (247) |
| umbral 5 pts | 467 | +0.071 | +18.3% | 0.0058 | 46% | 3.2 | 1.8 (244) |
| umbral 10 pts | 402 | +0.089 | +24.3% | 0.0055 | 46% | 3.7 | 2.5 (225) |

## Retraso de ejecución 10 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 472 | +0.075 | +18.2% | 0.0059 | 49% | 3.5 | 2.2 (245) |
| umbral 5 pts | 455 | +0.065 | +16.4% | 0.0059 | 47% | 3.0 | 1.5 (242) |
| umbral 10 pts | 396 | +0.074 | +19.7% | 0.0057 | 46% | 3.2 | 2.2 (225) |

## Retraso de ejecución 30 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 449 | +0.072 | +17.5% | 0.0056 | 49% | 3.5 | 2.2 (240) |
| umbral 5 pts | 430 | +0.059 | +14.5% | 0.0056 | 47% | 2.7 | 1.5 (235) |
| umbral 10 pts | 379 | +0.074 | +19.8% | 0.0053 | 46% | 3.2 | 2.3 (222) |

## Desglose (retraso 5 s, umbral 5 pts)

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| 1ª mitad | 228 | +0.026 | +6.3% | 0.0061 | 44% | 0.9 | 0.1 (111) |
| 2ª mitad | 239 | +0.114 | +31.3% | 0.0054 | 49% | 3.6 | 2.1 (133) |
| mercados de 5 min | 355 | +0.094 | +26.1% | 0.0053 | 46% | 3.8 | 2.6 (198) |
| mercados de 15 min | 63 | +0.080 | +19.7% | 0.0063 | 49% | 1.4 | 1.3 (44) |
| mercados de 60 min | 41 | -0.106 | -20.7% | 0.0085 | 41% | -1.4 | -1.6 (21) |
| mercados de 1440 min | 8 | -0.107 | -12.6% | 0.0074 | 75% | -0.7 | -0.4 (3) |
| BTCUSDT | 155 | +0.067 | +16.8% | 0.0059 | 47% | 1.7 | 1.7 (149) |
| ETHUSDT | 160 | +0.078 | +20.0% | 0.0057 | 48% | 2.1 | 2.1 (155) |
| SOLUSDT | 152 | +0.068 | +18.1% | 0.0057 | 45% | 1.8 | 1.4 (144) |
| lado up | 224 | +0.095 | +24.5% | 0.0057 | 49% | 2.9 | 1.9 (136) |
| lado down | 243 | +0.049 | +12.7% | 0.0059 | 44% | 1.7 | 0.4 (146) |

## Tamaño disponible al ejecutar (mejor nivel del libro L2)

- Apuestas con libro: 467 de 467. US$ en el mejor nivel: mediana 20, p25 8, p75 62.
- Antigüedad del snapshot L2 usado: mediana 2 s (el libro se graba por snapshots).
- Ganancia neta tomando solo el mejor nivel (tope US$ 1.000 por apuesta): US$ 8,647 en 4.1 días (≈ US$ 2,123/día). Cota optimista: supone que nadie se lo llevó antes.
- Con tope US$ 100 por apuesta (más realista para empezar): US$ 5,841 (≈ US$ 1,434/día).

## Control del BBO grabado (bug de orden en el recorder)

- Apuestas con snapshot L2 de ≤30 s: 421. Precio del BBO = mejor nivel L2 (±1 centavo) en el 51% de los casos.
- Si el edge es real, tiene que sobrevivir usando el precio del libro L2:

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| con precio BBO (original) | 421 | +0.075 | +19.5% | 0.0056 | 46% | 3.2 | 2.0 (215) |
| con precio L2 (control) | 421 | +0.070 | +18.2% | 0.0056 | 46% | 3.0 | 1.8 (215) |

## Cómo leerlo

- Vale si el neto por US$ es positivo con retraso de 10-30 s, en ambas mitades y con t por ventana > 2.
- Si muere al pasar de 5 a 10 s, es arbitraje de latencia: requiere un bot rápido y el tamaño manda.
- El tamaño en el mejor nivel limita cuánto se puede ganar por día, por bueno que sea el edge.