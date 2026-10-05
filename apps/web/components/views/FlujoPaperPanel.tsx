import React, { useEffect, useRef, useState } from "react";
import { Activity } from "lucide-react";

/** Paper trading en vivo: comparación de todas las cuentas y detalle de la elegida (precios de Binance cada 5 s). */
export function FlujoPaperPanel() {
  const api = process.env.NEXT_PUBLIC_API_URL || "";
  const [d, setD] = useState<any>(null);
  const [all, setAll] = useState<any[]>([]);
  const [cuenta, setCuenta] = useState<string>("flujo_v1");
  const [err, setErr] = useState<string>("");
  const timer = useRef<any>(null);

  const poll = async (c: string) => {
    try {
      const [r, r2] = await Promise.all([fetch(`${api}/api/research/paper_flujo_live?cuenta=${c}`),
                                         fetch(`${api}/api/research/paper_cuentas`)]);
      if (r.ok) { setD(await r.json()); setErr(""); } else setErr(`El backend respondió ${r.status}`);
      if (r2.ok) setAll((await r2.json()).cuentas || []);
    } catch { setErr("No me puedo comunicar con el backend (¿se está reiniciando?)."); }
  };
  useEffect(() => {
    poll(cuenta);
    clearInterval(timer.current);
    timer.current = setInterval(() => poll(cuenta), 5000);
    return () => clearInterval(timer.current);
  }, [cuenta]);

  const usd = (x: any, dec = 2) => (x === null || x === undefined ? "—" :
    `${x < 0 ? "-" : ""}$${Math.abs(x).toLocaleString(undefined, { minimumFractionDigits: dec, maximumFractionDigits: dec })}`);
  const pct = (x: any) => (x === null || x === undefined ? "—" : `${x >= 0 ? "+" : ""}${x.toFixed(2)}%`);
  const tone = (x: any) => (x === null || x === undefined ? "text-slate-400" : x >= 0 ? "text-emerald-400" : "text-rose-400");
  const price = (x: any) => (x === null || x === undefined ? "—" : x >= 100 ? x.toFixed(2) : x >= 1 ? x.toFixed(4) : x.toPrecision(4));

  if (!d) return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-xs font-mono-code text-slate-400">
      Cargando paper del flujo comprador... {err}
    </div>
  );
  const Compare = () => (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead><tr className="text-slate-500 text-left">
          <th className="py-1">Cuenta (clic para ver)</th><th>Capital</th><th>Resultado</th><th>Posiciones</th><th>Costos + funding</th>
        </tr></thead>
        <tbody>
          {all.map((c) => (
            <tr key={c.cuenta} onClick={() => setCuenta(c.cuenta)}
              className={`border-t border-slate-800/60 cursor-pointer hover:bg-slate-900 ${c.cuenta === cuenta ? "bg-slate-900/80" : ""}`}>
              <td className="py-1 text-slate-100">{c.descripcion}{c.examen && (
                <span className={`ml-2 px-1 rounded ${c.examen.estado === "PASO" ? "bg-emerald-900 text-emerald-300" :
                  c.examen.estado === "QUEMO" ? "bg-rose-900 text-rose-300" : "bg-cyan-900/60 text-cyan-300"}`}>
                  intento {c.examen.intento}: {c.examen.estado === "EN_CURSO" ? "en curso" : c.examen.estado === "PASO" ? "PASÓ" : "QUEMÓ"}
                </span>)}</td>
              <td className="text-slate-200">{usd(c.equity)}</td>
              <td className={tone(c.ganancia_pct)}>{pct(c.ganancia_pct)}</td>
              <td className="text-slate-400">{c.posiciones}</td>
              <td className="text-slate-400">{usd(c.costos_y_funding)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  if (d.estado === "SIN_ARRANCAR") return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-xs font-mono-code text-slate-400 space-y-3">
      <Compare />
      <div>Esta cuenta todavía no arrancó (arranca sola con el recorder, en el primer minuto).</div>
    </div>
  );

  const rows: any[] = d.posiciones || [];
  const longs = rows.filter((r) => r.lado === "COMPRA");
  const shorts = rows.filter((r) => r.lado === "VENTA");
  const hist: any[] = d.equity_diaria || [];
  const next = d.proximo_rebalanceo ? new Date(d.proximo_rebalanceo) : null;
  const left = next ? Math.max(0, next.getTime() - Date.now()) : 0;
  const dd = Math.floor(left / 86400000), hh = Math.floor((left % 86400000) / 3600000);

  // curva de capital (diaria) en SVG simple
  const vals = hist.map((h) => h.equity);
  const lo = Math.min(...vals, d.capital_inicial), hi = Math.max(...vals, d.capital_inicial);
  const W = 300, H = 60;
  const pts = vals.map((v, i) => `${vals.length > 1 ? (i / (vals.length - 1)) * W : W / 2},${H - ((v - lo) / ((hi - lo) || 1)) * H}`).join(" ");


  const exRow = all.find((c) => c.examen);
  const ex = exRow?.examen;
  const Bar = ({ label, value, max, color, text }: { label: string; value: number; max: number; color: string; text: string }) => (
    <div>
      <div className="flex justify-between text-slate-400"><span>{label}</span><span className="text-slate-200">{text}</span></div>
      <div className="h-2 bg-slate-800 rounded"><div className={`h-2 rounded ${color}`}
        style={{ width: `${Math.max(0, Math.min(100, (value / (max || 1)) * 100))}%` }} /></div>
    </div>
  );
  const ExamBox = () => {
    if (!ex) return null;
    const c0 = exRow.capital_inicial ?? 10000;
    const eqv = exRow.equity ?? c0;
    const fin = ex.estado !== "EN_CURSO";
    return (
      <div className={`rounded border p-3 space-y-2 ${ex.estado === "PASO" ? "border-emerald-700" : ex.estado === "QUEMO" ? "border-rose-700" : "border-cyan-800"}`}>
        <div className="text-slate-100 font-semibold">
          Examen HyroTrader 1 fase a 2x — intento {ex.intento} · capital {usd(exRow.equity)}{" "}
          {fin ? <span className={ex.estado === "PASO" ? "text-emerald-400" : "text-rose-400"}>
            {ex.estado === "PASO" ? "PASÓ" : "QUEMÓ"} ({ex.motivo}). Arranca otro intento mañana 00:05 UTC.</span>
            : <span className="text-slate-400">en curso desde {new Date(ex.inicio).toLocaleString()}</span>}
        </div>
        {!fin && (
          <div className="grid md:grid-cols-3 gap-4">
            <Bar label="Avance al objetivo (+10%)" value={eqv - c0} max={ex.objetivo_usd - c0} color="bg-emerald-500"
              text={`falta ${usd(ex.falta_para_pasar_usd, 0)}`} />
            <Bar label="Margen antes de quemar (−6% total)" value={ex.margen_total_usd} max={c0 - ex.piso_total_usd}
              color={ex.margen_total_usd < (c0 - ex.piso_total_usd) * 0.33 ? "bg-rose-500" : "bg-amber-500"}
              text={usd(ex.margen_total_usd, 0)} />
            <Bar label="Margen de hoy (−4% en el día)" value={ex.margen_hoy_usd} max={ex.limite_diario_usd}
              color={ex.margen_hoy_usd < ex.limite_diario_usd * 0.33 ? "bg-rose-500" : "bg-amber-500"}
              text={`${usd(ex.margen_hoy_usd, 0)} (hoy ${usd(ex.pnl_hoy_usd, 0)})`} />
          </div>
        )}
        <div className="text-slate-500">
          Días operados {ex.dias_operados}/{ex.dias_minimos} mínimo · mejor día {usd(ex.mejor_dia_usd, 0)} (no puede ser ≥ 40% de la ganancia)
          {ex.historial?.length > 0 && <> · intentos anteriores: {ex.historial.map((h: any) =>
            `#${h.intento} ${h.estado === "PASO" ? "pasó" : "quemó"} en ${h.dias} d`).join(", ")}</>}
        </div>
      </div>
    );
  };

  const Table = ({ title, list }: { title: string; list: any[] }) => (
    <div className="flex-1 min-w-[320px]">
      <div className="text-slate-300 font-semibold mb-1">{title} ({list.length})</div>
      <table className="w-full">
        <thead><tr className="text-slate-500 text-left">
          <th className="py-1">Cripto</th><th>Entró a</th><th>Ahora</th><th>Monto</th><th className="text-right">Resultado</th>
        </tr></thead>
        <tbody>
          {list.map((r) => (
            <tr key={r.symbol} className="border-t border-slate-800/60">
              <td className="py-1 text-slate-100">{r.symbol.replace("USDT", "")}</td>
              <td className="text-slate-400">{price(r.entrada)}</td>
              <td className="text-slate-200">{price(r.precio)}</td>
              <td className="text-slate-400">{usd(r.valor_usd, 0)}</td>
              <td className={`text-right ${tone(r.ganancia_usd)}`}>{usd(r.ganancia_usd)} ({pct(r.ganancia_pct)})</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="rounded-lg border border-cyan-900/60 bg-slate-950/40 p-4 text-xs font-mono-code space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <Activity className="w-4 h-4 text-cyan-400" />
        <span className="text-slate-100 font-semibold">Paper en vivo — {d.descripcion || "Flujo comprador V1"}</span>
        <span className="text-slate-500">plata de mentira · precios reales de Binance · se actualiza cada 5 s</span>
        {err && <span className="text-rose-300">{err}</span>}
      </div>
      <ExamBox />
      <Compare />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div><div className="text-slate-500">Capital ahora</div><div className="text-lg text-slate-100">{usd(d.equity)}</div></div>
        <div><div className="text-slate-500">Desde el inicio</div><div className={`text-lg ${tone(d.ganancia_total_usd)}`}>{usd(d.ganancia_total_usd)} ({pct(d.ganancia_total_pct)})</div></div>
        <div><div className="text-slate-500">Hoy</div><div className={`text-lg ${tone(d.ganancia_hoy_usd)}`}>{usd(d.ganancia_hoy_usd)}</div></div>
        <div><div className="text-slate-500">Costos + funding</div><div className="text-lg text-slate-300">{usd((d.costos_pagados || 0) + (d.funding_pagado || 0))}</div></div>
        <div><div className="text-slate-500">Próximo rebalanceo</div><div className="text-lg text-slate-300">{next ? `en ${dd} d ${hh} h` : "—"}</div></div>
      </div>
      {vals.length > 1 && (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-16"><polyline points={pts} fill="none" stroke="#22d3ee" strokeWidth="1.5" /></svg>
      )}
      <div className="flex flex-wrap gap-6">
        <Table title="Comprado" list={longs} />
        <Table title="Vendido en corto" list={shorts} />
      </div>
      <div className="text-slate-500">Arrancó {new Date(d.desde).toLocaleString()} con {usd(d.capital_inicial, 0)} a {d.apalancamiento}x · {d.rebalanceos} rebalanceo(s)</div>
    </div>
  );
}
