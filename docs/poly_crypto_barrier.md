# Mercados de precio cripto de Polymarket contra un modelo de volatilidad con Binance

172 mercados resueltos con strike en dólares; 10,239 observaciones diarias válidas. Cada día: precio del Sí de Polymarket contra el valor justo con Binance de ayer (σ de 30 días, sin deriva).

## 1. Calibración del mercado solo: precio del Sí → cuántas veces resolvió Sí

| precio del Sí | mercados | resolvió Sí | diferencia | t |
|---|---|---|---|---|
| 0.0–0.1 | 78 | 3% (esperado 6%) | -3.5 pts | -0.6 |
| 0.1–0.2 | 68 | 13% (esperado 16%) | -2.9 pts | -0.1 |
| 0.2–0.3 | 60 | 23% (esperado 26%) | -3.1 pts | 0.6 |
| 0.3–0.4 | 61 | 33% (esperado 36%) | -3.4 pts | -0.2 |
| 0.4–0.5 | 61 | 43% (esperado 46%) | -3.1 pts | -0.5 |
| 0.5–0.6 | 58 | 53% (esperado 54%) | -1.0 pts | -1.0 |
| 0.6–0.7 | 58 | 55% (esperado 64%) | -8.6 pts | -2.3 |
| 0.7–0.8 | 44 | 75% (esperado 74%) | +0.6 pts | -1.9 |
| 0.8–0.9 | 43 | 81% (esperado 83%) | -2.1 pts | -2.2 |
| 0.9–1.0 | 26 | 92% (esperado 92%) | -0.1 pts | -0.9 |

## 2. Mercado contra modelo: primer día con diferencia ≥ δ, comprar el lado barato (costo 1.5 centavos)

| δ | lado | mercados | resultado medio por acción | t (por grupo) | aciertos | 1ª mitad | 2ª mitad |
|---|---|---|---|---|---|---|---|
| 0.05 | vender (mercado > modelo): comprar No | 100 | +2.0 pts | 0.7 (41) | 61% | +13.3 (53) | -10.8 (47) |
| 0.05 | comprar Sí (modelo > mercado) | 61 | +6.1 pts | -0.0 (26) | 51% | -15.0 (24) | +19.7 (37) |
| 0.10 | vender (mercado > modelo): comprar No | 73 | +1.8 pts | 1.0 (26) | 59% | +20.3 (38) | -18.4 (35) |
| 0.10 | comprar Sí (modelo > mercado) | 37 | +6.6 pts | -0.1 (15) | 49% | -29.7 (11) | +22.0 (26) |
| 0.15 | vender (mercado > modelo): comprar No | 49 | -1.2 pts | 0.8 (16) | 49% | +32.2 (23) | -30.8 (26) |
| 0.15 | comprar Sí (modelo > mercado) | 25 | +8.1 pts | 0.4 (11) | 48% | -24.2 (8) | +23.3 (17) |
| 0.25 | vender (mercado > modelo): comprar No | 21 | -17.4 pts | -0.5 (9) | 24% | +31.1 (6) | -36.8 (15) |
| 0.25 | comprar Sí (modelo > mercado) | 3 | | | | | |

Resultado por acción: 0 = apuesta justa. Un grupo = mismo activo y misma fecha de cierre (los strikes de un mes se mueven juntos). Para que valga: positivo con t > 2 y con el mismo signo en las dos mitades.