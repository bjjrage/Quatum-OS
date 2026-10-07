# Estrategias propuestas a partir de las recordings (6 oct 2026)

Son **hipótesis diseñadas antes de ver resultados**, no edges confirmados. Cada una tiene regla, costo, prueba y criterio de descarte. Número máximo de variantes por estrategia: 8 (ya hay ≥274 pruebas acumuladas; cada variante extra erosiona la validez estadística).

## Qué dicen los datos y qué permiten

- Tick-level de Binance perp, Deribit y Polymarket: ~4 días, ~83 % de uptime (huecos de 8,1 h, 3,0 h, 1,5 h). Pump.fun: ~1,7 días.
- Eso alcanza para **eventos frecuentes** (miles de eventos), no para microestructura de régimen ni para eventos raros.
- Costos de referencia: Binance taker 4,5 bps por lado (≈10 bps ida y vuelta con spread); Pump.fun 1 % por lado.
- Descartado: scalping por flujo/imbalance con entrada taker. El edge de esas señales a 10-60 s suele ser de 1-3 bps y el costo ronda 10 bps. Solo `edge_scan` (estudio A) lo confirma o refuta.

## E1. Graduación de Pump.fun por hazard (la más testeable hoy)

**Hipótesis.** El precio en la bonding curve es una función conocida de las reservas. Si un token tiene alta probabilidad de graduarse pronto, el salto hasta la graduación es calculable. Entonces el valor esperado es `P(grad) × ganancia_hasta_graduación − (1−P) × pérdida`.

**Datos.** `pumpfun_trades` (6,2 M filas) con `real_token_reserves`, `virtual_*_reserves`, `user`, `is_buy`; `pumpfun_completes` (1.708 eventos); `pumpfun_creates`.

**Señal.**
- Progreso de la curva = `1 − real_token_reserves / real_token_reserves_inicial`. Verificar la constante inicial con el primer trade de cada mint, sin asumirla.
- Features a t = 5 min: progreso, compradores únicos nuevos en los últimos 2 min, SOL neto en 5 min, proporción de compras, concentración (top-3 wallets / volumen).
- Modelo: regresión logística, con calibración en la 1ª mitad y prueba en la 2ª. Target: graduación en los siguientes 15 min.

**Regla.** Comprar si `P(grad) ≥ umbral` y el progreso está entre 30 % y 75 %. Vender al graduarse o en un stop temporal de 15 min. Tamaño fijo, chico.

**Costo.** 2 % ida y vuelta más slippage. Hace falta `P × ganancia_a_graduar > 2 % + slippage`. La ganancia a graduar se calcula exactamente desde la curva, para cada progreso.

**Descarte.**
- El EV neto OOS no es positivo en ambas mitades.
- El resultado depende de salidas con precio rancio. El script ya mide la fracción `stale`; más del 40 % invalida el resultado.
- El AUC OOS es menor que 0,60.

**Riesgo principal.** Asimetría: pérdidas frecuentes y chicas, ganancias raras. Con 1.708 graduaciones, la incertidumbre del EV es grande; exigir intervalo de confianza por bloques horarios.

## E2. Reversión tras cascada de liquidaciones, con entrada maker

**Hipótesis.** Una ráfaga de liquidaciones forzadas empuja el precio más allá del valor justo. El rebote es de unos minutos. El problema de STR-002 es pagar taker en un momento de spread ancho.

**Datos.** `forced_liquidations` (83 k eventos), `bbo_ticks`, `trade_ticks` de Binance; BTC y ETH como factores.

**Señal.**
- Ráfaga = suma de notional liquidado en 60 s ≥ p99 del símbolo.
- Desplazamiento = retorno de 60 s del símbolo menos `β·BTC` menos `γ·ETH` (el residual de STR-002) ≤ −k·σ.
- Solo largo, como exige tu invariante (liquidación de largos y caída residual).
- Filtro: DVOL de Deribit por debajo de un umbral. En pánico de mercado se cancela.

**Entrada.** Escalera de 3 órdenes límite por debajo del mid (por ejemplo −5, −10 y −15 bps), con cancelación a los 120 s. Esto es lo que cambia el costo (maker 2 bps) pero introduce selección adversa: se llena más cuando el precio sigue cayendo. Medirlo es parte de la prueba.

**Salida.** Reversión a la referencia pre-ráfaga (mid 60 s antes) o salida temporal a 10 min, lo que ocurra primero. Stop duro en −1,5 × el desplazamiento.

**Descarte.**
- Con entrada simulada en el precio de las órdenes y solo cuando el precio las cruza, el neto OOS (incluyendo el costo de las no ejecutadas) no es positivo.
- Menos de 150 eventos útiles tras 4 semanas de datos.
- Funciona solo en BTC/ETH-beta alto y no en altcoins (la tesis es altcoins).

**Limitación.** 83 k liquidaciones en 4 días dan unas pocas centenas de ráfagas p99. Hace falta más captura (objetivo ≥ 4 semanas) antes de concluir.

## E3. Valor justo de los mercados cortos de Polymarket (cripto) contra Binance/Deribit

**Hipótesis.** En los mercados de Polymarket del tipo "¿BTC sube/cierra sobre K a la hora T?", el precio puede ir rezagado respecto de Binance. Se puede calcular el valor justo como opción digital: `P = N(d2)`, con el mid de Binance como spot, y la volatilidad de Deribit (IV, o DVOL para un nivel agregado) o la realizada.

**Datos.** `polymarket/bbo_ticks` (116 M filas), `orderbook_l2_depth`, `polymarket_metadata_history` (pregunta, `end_date_iso`, `clob_token_ids_json`, `fee_schedule_raw_json`), más Binance y Deribit.

**Paso previo.** Mapear `symbol` (token id) a mercado y a su condición vía metadata. Filtrar solo mercados cripto de precio con vencimiento ≤ 24 h.

**Señal.** `edge = precio_modelo − precio_polymarket` por lado (usando ask para comprar, bid para vender). Operar si `|edge| > fee + spread_polymarket + margen`. Margen de partida: 2 puntos de probabilidad.

**Salida.** Mantener hasta convergencia (|edge| < 0,5 pt), o a vencimiento, o stop por tiempo.

**Descarte.**
- El neto OOS después de fees y spread no es positivo.
- El edge desaparece con el rezago de ejecución realista (latencia a Polymarket de 1-2 s).
- El `edge` está dominado por mercados ilíquidos (spread > 3 pt), donde no hay tamaño.

**Por qué es la más interesante.** Es el único lugar donde tus datos aportan algo que el mercado público no ofrece de forma trivial. Va en la misma línea que STR-001 y reutiliza su modelo Black-76. Tiene el riesgo de que la liquidez disponible sea chica.

## E4. Filtro de régimen (no es una estrategia sola)

Usar DVOL, funding y el uptime del recorder como compuerta global:
- Sin posiciones nuevas si DVOL supera el p90 de su historia reciente.
- Sin posiciones nuevas si el recorder reporta datos con edad `observed_event_age_ns` fuera de rango (feed degradado).

Se prueba comparando E2 con y sin filtro, sin agregar más parámetros.

## Orden de trabajo recomendado

1. **E1** (pump graduation): se puede probar ya con los datos que tenés.
2. **E3** (Polymarket): requiere el mapeo token→mercado; es el mayor upside.
3. **E2** (liquidaciones): seguir capturando ≥ 4 semanas y mientras tanto correr el estudio B de `edge_scan`.
4. En paralelo, arreglar el recorder para subir el uptime del 83 % a más de 98 %: cada hueco de horas elimina eventos justo cuando hay volatilidad.

## Reglas para no engañarnos

- Calibrar en la 1ª mitad, juzgar en la 2ª. El signo debe ser igual en ambas.
- Costos incluidos desde el primer número que se mira.
- No ajustar umbrales después de ver el OOS. Si se cambia algo, el OOS queda consumido.
- Reportar siempre cuántas variantes se probaron.
