# Ciclo influencer en pump.fun: acumulación → post en X → pico → dump

Eventos con ventana completa (30 min antes, 120 min después del primer post): 3 de 10 tokens con post. Fee 1.25% por lado. Insiders = billeteras con compra neta en los 30 min previos al post.

## 1. Precio alrededor del post (mediana, 1.00 = precio al momento del post)

| -30m | -15m | -5m | -1m | +0m | +1m | +5m | +15m | +30m | +60m | +120m |
|---|---|---|---|---|---|---|---|---|---|---|
| nan | nan | 0.30 | 1.00 | 1.00 | 1.01 | 0.55 | 0.38 | 0.38 | 0.38 | 0.38 |

- Suba en los 30 min previos al post (mediana): nan% (el que llega con el post, llega tarde por esto).
- Minuto del pico tras el post: mediana 1.2; ≤1 min: 33%, ≤5 min: 67%, ≤15 min: 67%, ≤30 min: 67%

## 2. Cuándo venden los insiders (fracción de lo que tenían, mediana / p75)

| +5m | +15m | +30m | +60m | insiders por token (mediana) |
|---|---|---|---|---|
| 99% / 112% | 99% / 112% | 99% / 112% | 99% / 112% | 63 |

## 3. Entrar tras el post: salida fija vs salida cuando venden los insiders

Retorno neto en %, medio / mediano / acierto. `ins` = salir cuando los insiders vendieron ≥30% (tope 60 min).

| latencia | mitad | n | fijo 5m | fijo 15m | fijo 60m | ins |
|---|---|---|---|---|---|---|
| 10s | H1 | 1 | -66.4 / -66.4 / 0% | -66.4 / -66.4 / 0% | -66.4 / -66.4 / 0% | 17.3 / 17.3 / 100% |
| 10s | H2 | 1 | -62.8 / -62.8 / 0% | -72.5 / -72.5 / 0% | -72.7 / -72.7 / 0% | -2.5 / -2.5 / 0% |
| 60s | H1 | 1 | -67.7 / -67.7 / 0% | -67.7 / -67.7 / 0% | -67.7 / -67.7 / 0% | 12.8 / 12.8 / 100% |
| 60s | H2 | 1 | -67.2 / -67.2 / 0% | -67.3 / -67.3 / 0% | -67.5 / -67.5 / 0% | -2.5 / -2.5 / 0% |
| 300s | H1 | 1 | -2.5 / -2.5 / 0% | -2.5 / -2.5 / 0% | -2.5 / -2.5 / 0% | -2.5 / -2.5 / 0% |
| 300s | H2 | 1 | -27.9 / -27.9 / 0% | -28.3 / -28.3 / 0% | -28.3 / -28.3 / 0% | -2.5 / -2.5 / 0% |

## Cómo leerlo

- Si la suba previa al post es grande y el pico llega en pocos minutos: el post ES la salida de los insiders; entrar con el post solo sirve con latencia de segundos y salida muy rápida.
- Si `ins` gana a las salidas fijas en H1 y H2: vender cuando venden los que entraron antes es una regla de salida real.
- El edge de entrada no está en el post: está en detectar a los insiders ANTES (los grupos de pump_paper). Este estudio dice cuánto vale llegar antes y cuándo salir.