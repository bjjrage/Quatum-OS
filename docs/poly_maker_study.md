# ¿Gana un market maker en Polymarket up/down?

612,354 trades tomadores dentro de la ventana, 1146 mercados, 23.9 h.

## Todos los makers juntos

- Volumen US$ 7,797,090. Resultado bruto de los tomadores US$ +50,384 (+0.65%), fees pagadas US$ 77,375.
- Makers juntos (antes de devolución) US$ -50,384 (-0.65%); devolución 20% de las fees ≈ US$ 15,475.

| tiempo restante | volumen | makers juntos | por US$ |
|---|---|---|---|
| > 5 min | US$ 863,731 | US$ +10,570 | +1.22% |
| 2–5 min | US$ 3,984,010 | US$ -53,537 | -1.34% |
| 30 s–2 min | US$ 2,701,880 | US$ -10,650 | -0.39% |
| ≤30 s | US$ 247,468 | US$ +3,233 | +1.31% |

## Cotizador simulado (vende cada lado a justo + h, con Binance de `lag` s atrás)

| h (pts) | lag | llenadas | acciones | PnL US$ | por acción | t por ventana (n) | 1ª mitad | 2ª mitad |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 s | 279,624 | 2,816,370 | -359,817 | -12.78¢ | -6.0 (382) | -209,287 | -150,531 |
| 1 | 2 s | 281,030 | 2,829,941 | -373,409 | -13.19¢ | -6.1 (382) | -215,798 | -157,611 |
| 1 | 5 s | 300,948 | 3,021,933 | -448,141 | -14.83¢ | -7.3 (382) | -255,337 | -192,804 |
| 2 | 1 s | 258,604 | 2,598,331 | -332,194 | -12.78¢ | -5.6 (382) | -195,189 | -137,006 |
| 2 | 2 s | 260,034 | 2,610,193 | -345,276 | -13.23¢ | -5.7 (382) | -201,647 | -143,629 |
| 2 | 5 s | 280,865 | 2,808,977 | -416,701 | -14.83¢ | -6.9 (382) | -238,895 | -177,805 |
| 3 | 1 s | 238,691 | 2,389,828 | -308,532 | -12.91¢ | -5.3 (382) | -181,855 | -126,676 |
| 3 | 2 s | 239,748 | 2,398,335 | -319,909 | -13.34¢ | -5.4 (382) | -187,821 | -132,088 |
| 3 | 5 s | 261,300 | 2,604,307 | -386,638 | -14.85¢ | -6.5 (382) | -223,142 | -163,496 |
| 5 | 1 s | 204,087 | 2,024,907 | -265,547 | -13.11¢ | -4.8 (382) | -158,218 | -107,328 |
| 5 | 2 s | 204,815 | 2,031,547 | -276,028 | -13.59¢ | -4.9 (382) | -164,506 | -111,523 |
| 5 | 5 s | 226,536 | 2,240,152 | -337,329 | -15.06¢ | -5.9 (382) | -197,686 | -139,643 |

## Desglose del mejor con lag 2 s (h = 5 pts)

| grupo | llenadas | PnL US$ | t por ventana |
|---|---|---|---|
| BTC | 165,463 | -245,588 | -4.5 (382) |
| ETH | 26,454 | -21,912 | -3.9 (380) |
| SOL | 12,898 | -8,528 | -3.0 (376) |
| 5 min | 162,146 | -171,984 | -4.9 (287) |
| 15 min | 42,669 | -104,045 | -2.3 (95) |
| quedan > 2 min | 131,979 | -163,554 | -3.4 (382) |
| quedan ≤ 2 min | 72,836 | -112,474 | -6.4 (325) |

Optimista: supone que nuestra orden estaba primera en la fila a ese precio. Pesimista: la selección adversa está completa (resultados reales).