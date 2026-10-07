# Grupos reales vs bots en pump.fun

- Datos: 46.9 h. Detección en H1 (23.5 h), evaluación en H2.
- Filas con hora de cadena inválida (se usó la hora de recepción): 155 de 6,563,513.
- Billeteras con ≥3 tokens en H1: 45,598. Marcadas como bot: 32,028 (70%). Por motivo (se superponen): sniper 2,873, flipper 30,282, hiperactiva 3,102, monto fijo 2,772

## Cuántos grupos encuentra cada regla (H1)

- Regla vieja (pump_paper, {'window_slots': 2, 'min_shared': 3, 'min_overlap': 0.5, 'max_wallet_tokens': 150, 'max_burst': 40}): 2,136 grupos, 9,296 billeteras; tamaño mediano 3, p90 5, máximo 1,632
- Regla nueva: 163 grupos, 428 billeteras; tamaño mediano 2, p90 4, máximo 9

### Embudo de la regla nueva (pares de billeteras)

| paso | pares |
|---|---|
| pares que co-compran en ≥3 tokens (sin bots, minuto 1-30) | 493 |
| + solapamiento ≥30% | 466 |
| + lift ≥10x sobre el azar | 466 |
|   (de esos, copytrading descartado) | 24 |
| + no es copytrading | 442 |
| + venden juntos en ≥50% de los tokens | 395 |

### Pares más fuertes (regla nueva)

| billetera 1 | billetera 2 | tokens juntos | lift | venden juntos |
|---|---|---|---|---|
| `DFSmXvyE…` | `HdPw9ofw…` | 20 | 823x | 70% |
| `14FNE9ss…` | `2d4gSaBe…` | 17 | 726x | 88% |
| `14FNE9ss…` | `E5EvcNuA…` | 16 | 709x | 88% |
| `2d4gSaBe…` | `E5EvcNuA…` | 16 | 709x | 88% |
| `AWdf1xA3…` | `CjP6air8…` | 16 | 1945x | 94% |
| `CqTqoWfC…` | `DKtCHXT1…` | 14 | 988x | 100% |
| `FA78U9PS…` | `GQjdwQiu…` | 13 | 2064x | 92% |
| `5bu8P3QA…` | `BDCLHTNj…` | 13 | 1011x | 100% |
| `2FxDQ8Ea…` | `E7GGNLPL…` | 13 | 1011x | 100% |
| `2FxDQ8Ea…` | `5bu8P3QA…` | 13 | 1011x | 100% |

## ¿Predicen algo? (señales en H2, grupos detectados solo con H1)

Fee 1.25% por lado, entrada tras el siguiente trade. Retornos netos en %, medio / mediano. Ventana de 2 h para 2x, -50%, graduación y post en X (el vigilante de X no consulta todos los tokens).

| regla | n | neto 15m | neto 60m | toca 2x antes de -50% | toca -50% antes de 2x | gradúa ≤2h | post en X ≤2h |
|---|---|---|---|---|---|---|---|
| regla vieja: señales | 7,573 | -13.2 / -30.2 | -14.2 / -31.7 | 13% | 17% | 2.6% | 0.0% |
| regla vieja: control al azar | 7,436 | -0.8 / -2.5 | -2.2 / -2.5 | 3% | 5% | 0.9% | 0.0% |
| regla nueva: señales | 185 | -7.3 / -29.6 | -10.6 / -33.2 | 21% | 25% | 4.3% | 0.0% |
| regla nueva: control al azar | 184 | -6.0 / -2.5 | -6.4 / -2.5 | 4% | 7% | 1.6% | 0.0% |

## Cómo leerlo

- Una regla sirve si sus señales ganan claramente a su control al azar (mismo momento, misma edad y gente).
- Si la nueva gana y la vieja no, los 'grupos' viejos eran bots: cambiar la regla de pump_paper.
- Con ~1 día de evaluación, n chico: buscar diferencias grandes, no décimas.