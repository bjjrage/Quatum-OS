# HANDOFF Quant OS: todas las estrategias, qué falló, qué anduvo y por dónde seguir (2026-10-05)

Para quien tome el proyecto (otra sesión, un coder o Marcelo). Capital real: US$0. Todo es paper. Objetivo de fondo: encontrar una ventaja real y pasar el examen de una prop firm cripto (HyroTrader) rápido, sin esperar 10 meses.

## 0. Resumen en 6 líneas
1. De todo lo probado, NADA está confirmado como ventaja. Hay una candidata en Binance (flujo comprador) y una pista en pump.fun (billeteras con habilidad).
2. Lo técnico (velas, rebotes, momentum, cruces de la misma familia) no dio nada contra el azar con costos reales.
3. La única ventaja modesta en Binance es el flujo comprador (V1): Sharpe ~1,4 a 1,5, +24 a 26% anual, caída máxima 8 a 10%. Real pero chica. Sirve de base, no alcanza para un examen rápido a 1x.
4. La pista más fuerte es seguir el dinero en pump.fun: billeteras con historial de 2x. Mejora el acierto de 20% a ~31-35%, pero con muestra chica y ganancias concentradas en pocos tokens.
5. Seguir billeteras en Hyperliquid (para cripto de Binance) NO funciona: la rentabilidad no se repite.
6. Lo que decide ahora es el paper en vivo (~12 de octubre primera lectura seria) y datos NUEVOS grabados hacia adelante (no más velas).

## 1. Disciplina de pruebas (no negociable)
- Reglas fijadas ANTES de ver resultados, probadas una sola vez.
- Siempre contra un control al azar (misma salida, mismo número de entradas).
- Costos reales: Binance 0,04% comisión + 0,02% deslizamiento por lado + funding; pump.fun 1,25% por lado + 0,0005 SOL por envío.
- Último 30% reservado (corte 2025-05-19), corrección por cantidad de pruebas, permutaciones e intervalos bootstrap.
- Cada "descubrimiento" visto mirando resultados se descarta o se manda a paper hacia adelante.

## 2. Lo que se probó y falló (cerrado, no volver sin información nueva)

- STR-002 rebote 1-5 min (4 variantes, 90 d, 23 cripto): −0,10% a −0,11% por operación. Igual que entrar al azar. Bruto ya negativo.
- Análisis "tipo PYR" (65 cripto, 24 combinaciones): −0,10% por operación con costos reales. Todas iguales al azar. Sacar mitad al +1% sube aciertos 30%→45% pero el resultado no cambia.
- Laboratorio intradía: 150 ideas en velas de 1 h, 65 cripto, ~364 d: 0 pasan (mejor t 2,73 contra 3,4 exigido).
- Laboratorio de carteras días-semanas: 41 estrategias, 0 pasan (umbral t 3,03). Solo flujo comprador queda como candidata. Momentum y tendencia ganaron hasta 2025 y fallaron después.
- BTC lidera, alts siguen: las alts hacen ~110% de su movimiento en los mismos 5 s. Entrar 1-5 s después pierde 0,10 a 0,12%.
- Polymarket vs Binance (62 mercados "Up or Down" de 1 h): Polymarket predice igual o mejor. Apostar a la diferencia: −5 a −8 centavos por dólar antes de comisiones. Muestra chica (~30 apuestas).
- Cruces del flujo comprador con otras señales de velas (acumulación, persistencia, aceleración, doble, BTC sobre media de 50 d): ningún cruce supera claramente a V1. "Acumulación callada" es la peor (Sharpe −0,14). Cruzar señales de la MISMA familia no suma; hace falta información nueva.
- Flujo comprador V2 (4 variantes): ninguna supera a V1.
- Rotación de nichos de Binance por precio: pierde contra BTC en todas las variantes (x0,15 a x0,72). Se llega tarde.
- 23 reglas de nichos en Binance: 0 pasan (umbral t 2,85). Mejor en reservado: V1 + inicio de nicho 7 d, Sharpe 1,82, pero t de entrenamiento 2,38 < V1. Mejora posible, NO probada.
- Líder → rezagadas solo por precio (estudio histórico): negativo. Los líderes revierten −2% a −6,7%. Queda RECHAZADA solo por precio; la parte con X es solo paper hacia adelante.
- Billeteras en Hyperliquid (195 billeteras, 35 d contra 35 d): correlación del ROI entre ventanas 0,00. Las mejores (+61%) hicieron −21% después. Lo que persiste es estilo (scalpers) y tamaño de cuenta, no habilidad.
- pump.fun, grupos de billeteras que compran en el mismo slot (1.702 grupos): cuentas en vivo −99%. Son clusters de bots, más costos fijos y entrada sin ventaja. ARCHIVADAS.
- pump.fun, señales simples (compradores, SOL, ratio de venta, concentración, bots, edad): ninguna separa ganadores de perdedores.
- pump.fun, detector tarde (≥50 compradores): sin ventaja. Archivado.
- pump.fun, variaciones de salida con entrada sin ventaja: escalera −5,1%, fijo 1,5x −4,8%, fijo 2x −5,6%, fijo 3x −7,4%, trailing 35% −4,9%, aguantar 2 h −13,2%. La salida no arregla una mala entrada.

## 3. Lo que anduvo (con sus límites)

### 3.1 Flujo comprador V1 en Binance: la única candidata
- Qué es: comprar el 20% de cripto con más compra agresiva en 14 días, vender el 20% con menos, rebalanceo semanal, neutral al mercado, 65 cripto, datos 2022-03 a 2026-10.
- Resultados V1: Sharpe 1,41 entrenamiento / 1,56 reservado; +26% anual reservado; volatilidad 16%; caída máxima 10%; peor día −4,5%. Variante de 7 días: 1,41 / 1,47, +24%/año. Codex llegó solo a lo mismo.
- Robustez: de 60 variantes vecinas, 59 positivas en entrenamiento y 41 en reservado. Sharpe mediano 0,85 → 0,40. Ventaja real pero modesta (~8 a 20% anual).
- Limitaciones: solo criptos vivas hoy (sesgo de supervivencia), ~4 años, una sola familia de señal.
- Para HyroTrader: peor día −4,5% a 1x rompe el límite diario de 4% → operar ~0,7x. En simulación (reglas de Hyro SIN verificar): a 1x pasa ~70% pero tarda ~74 días; a 2x pasa ~50%, quema la cuenta ~50%, tarda ~25 días. La ventaja es demasiado chica para un examen rápido.
- Estado: paper hacia adelante con órdenes límite (mínimo 2 meses).

### 3.2 pump.fun: billeteras con habilidad (la pista más fuerte, sin confirmar)
- Regla fijada: billetera "buena" = ≥5 tokens vistos y ≥35% de aciertos a 2x; señal = ≥2 buenas entre los primeros 10 compradores. Decisión en la compra N°10, entrada en la operación siguiente.
- Prueba fuera de muestra: n=124, 34,7% llegan a 2x (base 20,8%), escalera +22% medio, control por permutación 20,9% (p<0,01).
- Versión en vivo honesta (crédito diferido): 74 señales en ~9 h, 31% a 2x, escalera +14% (IC95 −4% a +33%), mediana −23%.
- Límites: mediana por operación NEGATIVA, los 5 mejores tokens aportan 94% de la ganancia, el intervalo incluye 0 en la versión viva, solo ~17 h a 2 días de datos.
- Error corregido: acreditar el acierto al instante del 2x y los fallos recién a las 2 h infla las billeteras (la regla daba −15% real). Ahora el crédito es diferido.
- Sizing: con 35% de aciertos a 2x puede haber edge, pero comisiones y entradas chicas se la comen. Por eso las cuentas viejas se desangraron (mínimo 0,05 SOL, costo fijo ~2% extra sobre 2,5% de comisiones). Solución: tamaño fijo de 0,5 SOL por entrada.

### 3.3 Estructura de nichos (lo descriptivo sí es cierto)
- Los nichos rotan y el premio es enorme: saber de antemano el mejor nicho de cada trimestre daba x23,9 (~100%/año). En los trimestres malos caen todos juntos −50% a −70%.
- Detectarlos con precio no funciona. Lo que funciona algo es la compra agresiva (dinero entrando antes de que suba).
- Compra agresiva por nicho 7 d (largo/corto): Sharpe reservado 1,58. Rotar por compra agresiva 14 d solo compras: x2,19 total pero peor que BTC en reservado (x0,65 contra x0,76) y caída máxima 82%.

## 4. Visión
1. El análisis técnico en velas está agotado. Seguir inventando variantes es sobreajuste.
2. Para subir el acierto hace falta información de OTRA naturaleza: quién compra (billeteras), interés abierto, liquidaciones, profundidad del libro y atención/narrativa (X). Ninguna se puede backtestear bien: hay que grabar hacia adelante y medir en paper.
3. El camino más prometedor es CRUZAR dinero inteligente con filtros: pump.fun (billeteras buenas) + nicho caliente + (después) X. Cada pieza ya está en paper; el cruce se mide contra su control al azar.
4. Para el examen de la prop firm, V1 no alcanza solo. Opciones: (a) usarlo a ~0,7x como base lenta, (b) apilar una segunda ventaja no correlacionada si el paper se confirma, (c) no arriesgar el examen hasta tener al menos una ventaja confirmada en paper.
5. pump.fun (Solana, dinero propio) y HyroTrader (futuros) son mundos distintos: una ventaja en uno no se transfiere automáticamente al otro.

## 5. Estado del sistema
- Código en la PC: carpeta PORYECTOS\TRADING OS. Repo: github.com/bjjrage/Quatum-OS. Se arranca con start.bat. Usar "Guardar versión" antes de pasarle nada a un coder.
- Recorder (vigilante scripts/run_recorder.py): Binance WS + respaldo REST, Polymarket, Deribit, pump.fun. Reiniciado ~18:20 UTC del 2026-10-05.
- Paper en vivo:
  - Binance flujo comprador V1 (src/paper/flujo_paper.py).
  - Líder → rezagadas + X (src/paper/lider_paper.py): cuentas lider_x, lider_sin_x, lider_azar, lider_corto (hipótesis). Tope de X US$1/día. Un chequeo al día entre 00:05 y 06:00 UTC.
  - pump.fun (src/paper/pump_paper.py, SkillBook): billeteras (escalera), billeteras_2x (vende todo al 2x), billeteras_azar (control), nicho, nicho_azar. Tamaño fijo 0,5 SOL por entrada (20 SOL, máx. 30 abiertas). Grupos, detector tarde y azar viejo archivados.
- Herramientas: src/research/pump_tabla.py, POST /api/research/pump_compactar, laboratorios /api/backtests/lab, /plab (which=taker|v2|nichos), /rec, src/research/portfolio_lab.py.
- Tests: 756 pasando en mi copia (764 en la base del coder).
- Auditoría pre-paper del 3-oct y prompt de endurecimiento de 20 secciones para el coder. Verificado como real: `_mid_near` mira el futuro hasta 120 s; el respaldo REST de Binance mezcla filas sin marcar; el panel líder-rezagadas dice "sin eventos" aunque falle; `ultimo_chequeo_dia` y `asked.add` se marcan antes de saber si funcionó; hay dos presupuestos de X; hay un test tautológico (`or True`); textos dicen "la única que pasó las pruebas" cuando solo pasó una prueba interna.

## 6. Lo que NO probamos (o está sin verificar)
- Reglas oficiales de HyroTrader (objetivo 10%, pérdida diaria 4%, máxima 6%, mínimo 5 días, mejor día 40%): supuestas en el simulador.
- Costos de pump.fun (1,25% por lado, 0,0005 SOL por envío) y modelo de curva: sin cotejar con documentación ni ejecuciones reales. No se modeló deslizamiento ni propinas de prioridad.
- Descubrimiento de mercados de Polymarket por slug: no validado.
- Orden del libro de Polymarket (bids[0] podría ser el peor precio): nunca confirmado.
- Hyperliquid con ballenas, ventanas más largas, o la señal agregada de posiciones netas: sin historial.
- Interés abierto, liquidaciones, libro y funding en tiempo real como cruce del flujo comprador: se graban hacia adelante.
- Opciones/Deribit (STR-001): sin mapeo de mercados ni runner (bloqueante según la auditoría).
- Memes por tema y por cadena (líder → rezagadas versión meme): no construido.
- Universo de Binance más grande por nicho (hoy 65-66, con 18 de gaming y pocos de IA/DeFi/RWA).
- Un solo régimen grande de mercado (2022-2026) y sesgo de supervivencia.
- Recorder en la PC con huecos cuando se apaga: conviene un VPS antes de un mes de paper.

## 7. Lo que falta probar, en orden de prioridad
1. Hardening por el coder (prompt de 20 secciones). Antes: "Guardar versión" y exportar al repo los informes del Proyecto. Sin cambiar estrategias ni tocar capital.
2. Lectura de pump.fun ~12-oct (decenas de operaciones cerradas): billeteras contra billeteras_azar, billeteras contra billeteras_2x, nicho contra nicho_azar. Criterio: le gana al control y el IC95 no incluye 0. Si no, se archiva.
3. Seguir V1 en paper ≥ 2 meses; medir deslizamiento real.
4. Lectura de líder → rezagadas + X: lider_x contra lider_sin_x contra lider_azar, y si lider_corto confirma la reversión.
5. Señales de "no entrar" en pump.fun (creador vendió temprano, concentración de compradores).
6. Versión meme de líder → rezagadas por tema y por cadena.
7. Grabar datos nuevos de Binance hacia adelante (interés abierto, liquidaciones, libro, funding) y en 3-4 semanas cruzarlos con V1. Es el cruce con más potencial real.
8. Hyperliquid hacia adelante: grabar posiciones cada hora y medir contra el azar.
9. Verificar reglas de HyroTrader y costos de pump.fun contra la fuente oficial antes de decidir nada del examen.
10. Mover el recorder a un VPS y corregir los recorders de Polymarket si se sigue con STR-001.
11. Ampliar el universo de Binance por nicho y repetir "V1 + inicio de nicho 7 d" una sola vez.
12. Vista en el OS con una fila por estrategia (estado, operaciones cerradas, resultado contra su control, veredicto) y tabla de cruces manual y automática.

## 8. Reglas de colaboración que Marcelo pidió
- Hablarle en español y en términos simples. Me llama "Alberto".
- Avisarle explícitamente cuando termina un trabajo.
- NUNCA pasarle una ruta sin un link que funcione: describir la navegación de la interfaz.
- Claves solo por el archivo .env que él crea; nunca repetirlas. Preocupación por el costo de X (~US$1/día).
- Capital real USD 0. Nada de push ni merge a main sin autorización explícita. Líder → rezagadas solo por precio sigue RECHAZADA.
- Quiere resultados, no tocar código.
