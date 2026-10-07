# Polymarket up/down vs Binance: ¿es operable?

2202 mercados dentro del período. Fee por mercado según su `fee_schedule` grabado (`acciones × p × rate × (p(1−p))^exp`). Neto = después de fee. Precio = ask (o 1−bid) del bucket de 5 s posterior al retraso.

## Retraso de ejecución 5 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 448 | +0.092 | +23.3% | 0.0056 | 49% | 4.2 | 2.7 (233) |
| umbral 5 pts | 431 | +0.086 | +22.8% | 0.0056 | 47% | 3.8 | 2.4 (231) |
| umbral 10 pts | 368 | +0.107 | +30.8% | 0.0053 | 46% | 4.4 | 2.9 (211) |

## Retraso de ejecución 10 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 444 | +0.090 | +22.3% | 0.0058 | 50% | 4.1 | 2.7 (232) |
| umbral 5 pts | 425 | +0.083 | +21.4% | 0.0057 | 48% | 3.7 | 2.3 (230) |
| umbral 10 pts | 366 | +0.094 | +26.1% | 0.0054 | 46% | 3.9 | 2.6 (213) |

## Retraso de ejecución 30 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 415 | +0.090 | +22.5% | 0.0053 | 50% | 4.2 | 2.9 (225) |
| umbral 5 pts | 395 | +0.079 | +20.4% | 0.0054 | 47% | 3.5 | 2.3 (221) |
| umbral 10 pts | 342 | +0.098 | +27.9% | 0.0050 | 46% | 4.1 | 2.7 (205) |

## Desglose (retraso 5 s, umbral 5 pts)

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| 1ª mitad | 192 | +0.038 | +10.3% | 0.0056 | 42% | 1.2 | 0.3 (103) |
| 2ª mitad | 239 | +0.124 | +32.7% | 0.0055 | 51% | 3.9 | 2.8 (128) |
| mercados de 5 min | 356 | +0.105 | +28.9% | 0.0053 | 47% | 4.2 | 3.3 (196) |
| mercados de 15 min | 60 | +0.058 | +13.8% | 0.0065 | 48% | 1.0 | 1.1 (43) |
| mercados de 60 min | 15 | -0.253 | -49.4% | 0.0085 | 27% | -2.0 | -2.0 (12) |
| BTCUSDT | 142 | +0.078 | +20.6% | 0.0057 | 46% | 2.0 | 1.9 (138) |
| ETHUSDT | 148 | +0.092 | +25.1% | 0.0055 | 47% | 2.4 | 2.2 (144) |
| SOLUSDT | 141 | +0.086 | +22.8% | 0.0056 | 47% | 2.2 | 2.0 (136) |
| lado up | 206 | +0.113 | +31.1% | 0.0055 | 48% | 3.4 | 2.2 (129) |
| lado down | 225 | +0.061 | +15.7% | 0.0057 | 45% | 2.0 | 0.7 (135) |

## Tamaño disponible al ejecutar (mejor nivel del libro L2)

- Apuestas con libro: 431 de 431. US$ en el mejor nivel: mediana 19, p25 7, p75 61.
- Antigüedad del snapshot L2 usado: mediana 2 s (el libro se graba por snapshots).
- Ganancia neta tomando solo el mejor nivel (tope US$ 1.000 por apuesta): US$ 7,281 en 4.2 días (≈ US$ 1,725/día). Cota optimista: supone que nadie se lo llevó antes.
- Con tope US$ 100 por apuesta (más realista para empezar): US$ 6,306 (≈ US$ 1,494/día).

## Control del BBO grabado (bug de orden en el recorder)

- Apuestas con snapshot L2 de ≤30 s: 390. Precio del BBO = mejor nivel L2 (±1 centavo) en el 49% de los casos.
- Si el edge es real, tiene que sobrevivir usando el precio del libro L2:

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| con precio BBO (original) | 390 | +0.089 | +24.2% | 0.0055 | 46% | 3.8 | 2.5 (205) |
| con precio L2 (control) | 390 | +0.084 | +22.4% | 0.0055 | 46% | 3.5 | 2.3 (205) |

## Cómo leerlo

- Vale si el neto por US$ es positivo con retraso de 10-30 s, en ambas mitades y con t por ventana > 2.
- Si muere al pasar de 5 a 10 s, es arbitraje de latencia: requiere un bot rápido y el tamaño manda.
- El tamaño en el mejor nivel limita cuánto se puede ganar por día, por bueno que sea el edge.