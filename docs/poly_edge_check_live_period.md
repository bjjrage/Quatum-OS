# Polymarket up/down vs Binance: ¿es operable?

2217 mercados dentro del período. Fee por mercado según su `fee_schedule` grabado (`acciones × p × rate × (p(1−p))^exp`). Neto = después de fee. Precio = ask (o 1−bid) del bucket de 5 s posterior al retraso.

## Retraso de ejecución 5 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 453 | +0.092 | +23.4% | 0.0057 | 49% | 4.2 | 2.7 (236) |
| umbral 5 pts | 436 | +0.082 | +21.7% | 0.0056 | 47% | 3.6 | 2.3 (234) |
| umbral 10 pts | 371 | +0.108 | +30.8% | 0.0053 | 46% | 4.4 | 2.9 (214) |

## Retraso de ejecución 10 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 449 | +0.091 | +22.6% | 0.0058 | 50% | 4.2 | 2.8 (235) |
| umbral 5 pts | 430 | +0.079 | +20.3% | 0.0057 | 48% | 3.5 | 2.2 (233) |
| umbral 10 pts | 369 | +0.095 | +26.2% | 0.0054 | 46% | 4.0 | 2.6 (216) |

## Retraso de ejecución 30 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 419 | +0.093 | +23.3% | 0.0053 | 50% | 4.4 | 3.0 (228) |
| umbral 5 pts | 398 | +0.080 | +20.6% | 0.0054 | 47% | 3.6 | 2.4 (224) |
| umbral 10 pts | 345 | +0.099 | +27.9% | 0.0050 | 46% | 4.2 | 2.7 (208) |

## Desglose (retraso 5 s, umbral 5 pts)

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| 1ª mitad | 195 | +0.048 | +12.9% | 0.0056 | 43% | 1.5 | 0.7 (105) |
| 2ª mitad | 241 | +0.109 | +28.6% | 0.0056 | 50% | 3.5 | 2.5 (129) |
| mercados de 5 min | 360 | +0.100 | +27.3% | 0.0053 | 47% | 4.0 | 3.1 (198) |
| mercados de 15 min | 61 | +0.060 | +14.2% | 0.0065 | 49% | 1.0 | 1.2 (44) |
| mercados de 60 min | 15 | -0.253 | -49.4% | 0.0085 | 27% | -2.0 | -2.0 (12) |
| BTCUSDT | 143 | +0.072 | +18.7% | 0.0057 | 46% | 1.8 | 1.7 (139) |
| ETHUSDT | 149 | +0.088 | +23.9% | 0.0055 | 46% | 2.3 | 2.1 (145) |
| SOLUSDT | 144 | +0.086 | +22.5% | 0.0056 | 47% | 2.2 | 2.0 (139) |
| lado up | 207 | +0.116 | +32.1% | 0.0055 | 48% | 3.5 | 2.3 (130) |
| lado down | 229 | +0.051 | +13.0% | 0.0057 | 45% | 1.7 | 0.5 (138) |

## Tamaño disponible al ejecutar (mejor nivel del libro L2)

- Apuestas con libro: 436 de 436. US$ en el mejor nivel: mediana 20, p25 7, p75 62.
- Antigüedad del snapshot L2 usado: mediana 2 s (el libro se graba por snapshots).
- Ganancia neta tomando solo el mejor nivel (tope US$ 1.000 por apuesta): US$ 6,411 en 4.2 días (≈ US$ 1,515/día). Cota optimista: supone que nadie se lo llevó antes.
- Con tope US$ 100 por apuesta (más realista para empezar): US$ 6,202 (≈ US$ 1,466/día).

## Control del BBO grabado (bug de orden en el recorder)

- Apuestas con snapshot L2 de ≤30 s: 395. Precio del BBO = mejor nivel L2 (±1 centavo) en el 49% de los casos.
- Si el edge es real, tiene que sobrevivir usando el precio del libro L2:

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| con precio BBO (original) | 395 | +0.085 | +22.9% | 0.0055 | 46% | 3.6 | 2.4 (208) |
| con precio L2 (control) | 395 | +0.080 | +21.1% | 0.0055 | 46% | 3.3 | 2.2 (208) |

## Cómo leerlo

- Vale si el neto por US$ es positivo con retraso de 10-30 s, en ambas mitades y con t por ventana > 2.
- Si muere al pasar de 5 a 10 s, es arbitraje de latencia: requiere un bot rápido y el tamaño manda.
- El tamaño en el mejor nivel limita cuánto se puede ganar por día, por bueno que sea el edge.