# Polymarket up/down vs Binance: ¿es operable?

1977 mercados dentro del período. Fee por mercado según su `fee_schedule` grabado (`acciones × p × rate × (p(1−p))^exp`). Neto = después de fee. Precio = ask (o 1−bid) del bucket de 5 s posterior al retraso.

## Retraso de ejecución 5 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 466 | +0.073 | +18.0% | 0.0058 | 48% | 3.4 | 2.0 (239) |
| umbral 5 pts | 451 | +0.067 | +17.4% | 0.0058 | 46% | 3.0 | 1.5 (236) |
| umbral 10 pts | 388 | +0.078 | +21.2% | 0.0056 | 45% | 3.3 | 2.2 (216) |

## Retraso de ejecución 10 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 457 | +0.068 | +16.4% | 0.0060 | 49% | 3.1 | 1.9 (237) |
| umbral 5 pts | 440 | +0.060 | +15.0% | 0.0059 | 47% | 2.7 | 1.2 (234) |
| umbral 10 pts | 382 | +0.063 | +16.4% | 0.0057 | 45% | 2.6 | 1.8 (216) |

## Retraso de ejecución 30 s

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| umbral 3 pts | 433 | +0.064 | +15.5% | 0.0057 | 48% | 3.0 | 2.0 (232) |
| umbral 5 pts | 416 | +0.052 | +12.8% | 0.0057 | 46% | 2.3 | 1.2 (227) |
| umbral 10 pts | 365 | +0.065 | +17.1% | 0.0053 | 45% | 2.8 | 2.0 (213) |

## Desglose (retraso 5 s, umbral 5 pts)

| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |
|---|---|---|---|---|---|---|---|
| 1ª mitad | 220 | +0.038 | +9.4% | 0.0060 | 45% | 1.2 | 0.3 (108) |
| 2ª mitad | 231 | +0.095 | +25.7% | 0.0055 | 47% | 3.0 | 1.6 (128) |
| mercados de 5 min | 342 | +0.093 | +25.6% | 0.0053 | 46% | 3.6 | 2.4 (190) |
| mercados de 15 min | 61 | +0.072 | +18.1% | 0.0061 | 48% | 1.3 | 1.2 (43) |
| mercados de 60 min | 40 | -0.119 | -23.3% | 0.0085 | 40% | -1.5 | -1.9 (20) |
| mercados de 1440 min | 8 | -0.107 | -12.6% | 0.0074 | 75% | -0.7 | -0.4 (3) |
| BTCUSDT | 150 | +0.069 | +17.3% | 0.0058 | 47% | 1.7 | 1.8 (144) |
| ETHUSDT | 155 | +0.065 | +16.8% | 0.0057 | 46% | 1.7 | 1.7 (150) |
| SOLUSDT | 146 | +0.069 | +18.2% | 0.0058 | 45% | 1.8 | 1.4 (138) |
| lado up | 215 | +0.095 | +25.0% | 0.0056 | 48% | 2.9 | 2.0 (129) |
| lado down | 236 | +0.042 | +10.7% | 0.0059 | 44% | 1.4 | 0.0 (142) |

## Tamaño disponible al ejecutar (mejor nivel del libro L2)

- Apuestas con libro: 451 de 451. US$ en el mejor nivel: mediana 19, p25 7, p75 61.
- Antigüedad del snapshot L2 usado: mediana 2 s (el libro se graba por snapshots).
- Ganancia neta tomando solo el mejor nivel (tope US$ 1.000 por apuesta): US$ 6,357 en 4.0 días (≈ US$ 1,576/día). Cota optimista: supone que nadie se lo llevó antes.

## Cómo leerlo

- Vale si el neto por US$ es positivo con retraso de 10-30 s, en ambas mitades y con t por ventana > 2.
- Si muere al pasar de 5 a 10 s, es arbitraje de latencia: requiere un bot rápido y el tamaño manda.
- El tamaño en el mejor nivel limita cuánto se puede ganar por día, por bueno que sea el edge.