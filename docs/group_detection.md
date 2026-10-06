# Grupos reales vs bots en pump.fun

- Datos: 5104079577683545.0 h. Detección en H1 (2552039788841772.5 h), evaluación en H2.
- Billeteras con ≥3 tokens en H1: 0. Marcadas como bot: 0 (nan%). Por motivo (se superponen): sniper 0, flipper 0, hiperactiva 0, monto fijo 0

## Cuántos grupos encuentra cada regla (H1)

- Regla vieja (pump_paper, {'window_slots': 2, 'min_shared': 3, 'min_overlap': 0.5, 'max_wallet_tokens': 150, 'max_burst': 40}): 0 grupos
- Regla nueva: 0 grupos

### Embudo de la regla nueva (pares de billeteras)

| paso | pares |
|---|---|
| pares que co-compran en ≥3 tokens (sin bots, minuto 1-30) | 0 |

## ¿Predicen algo? (señales en H2, grupos detectados solo con H1)

Fee 1.25% por lado, entrada tras el siguiente trade. Retornos netos en %, medio / mediano. Ventana de 2 h para 2x, -50%, graduación y post en X (el vigilante de X no consulta todos los tokens).

| regla | n | neto 15m | neto 60m | toca 2x antes de -50% | toca -50% antes de 2x | gradúa ≤2h | post en X ≤2h |
|---|---|---|---|---|---|---|---|
| regla vieja: señales | 0 | - | - | - | - | - | - |
| regla vieja: control al azar | 0 | - | - | - | - | - | - |
| regla nueva: señales | 0 | - | - | - | - | - | - |
| regla nueva: control al azar | 0 | - | - | - | - | - | - |

## Cómo leerlo

- Una regla sirve si sus señales ganan claramente a su control al azar (mismo momento, misma edad y gente).
- Si la nueva gana y la vieja no, los 'grupos' viejos eran bots: cambiar la regla de pump_paper.
- Con ~1 día de evaluación, n chico: buscar diferencias grandes, no décimas.