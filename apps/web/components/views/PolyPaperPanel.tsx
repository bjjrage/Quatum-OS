import React, { useEffect, useState } from "react";
import { Target } from "lucide-react";

/** Paper en vivo: mercados "¿sube o baja?" de Polymarket (5 y 15 min) contra el precio de Binance. */
export function PolyPaperPanel() {
  const api = process.env.NEXT_PUBLIC_API_URL || "";
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${api}/api/research/poly_paper`);
        if (r.ok) { setD(await r.json()); setErr(""); } else setErr(`El backend respondió ${r.status}`);
      } catch { setErr("No me puedo comunicar con el backend."); }
    };
    poll();
    const t = setInterval(poll, 10000);
    return () => clearInterval(t);
  }, []);
  const n = (x: any, dec = 2) => (x === null || x === undefined ? "—" : Number(x).toFixed(dec));
  const tone = (x: any) => (x === null || x === undefined ? "text-slate-400" : x >= 0 ? "text-emerald-400" : "text-rose-400");
  const hora = (t: any) => (t ? new Date(Number(t) * 1000).toLocaleTimeString() : "—");
  const ult: any[] = d?.ultimas || [];
  const crit = d?.criterio;
  return (
    <div className="rounded-lg border border-sky-900/60 bg-slate-950/40 p-4 text-xs font-mono-code space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <Target className="w-4 h-4 text-sky-400" />
        <span className="text-slate-100 font-semibold">Polymarket "¿sube o baja?" vs Binance — paper en vivo</span>
        <span className="text-slate-500">
          BTC/ETH/SOL · 5 y 15 min · umbral {d?.config ? n(d.config.threshold * 100, 0) : "—"} pts · orden a {d?.config?.delay_s ?? "—"} s ·
          tope US$ {d?.config?.max_usd ?? "—"} · fees reales · sin órdenes reales
        </span>
        <span className={d?.corriendo ? "text-emerald-400" : "text-amber-300"}>
          {d?.corriendo ? "● corriendo" : "○ detenido (correr scripts/run_poly_updown_paper.py)"}
        </span>
        {err && <span className="text-rose-300">{err}</span>}
      </div>
      {!d || !d.senales ? (
        <div className="text-slate-400">Sin señales todavía (calienta 30 min para medir la volatilidad antes de apostar).</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div><div className="text-slate-500">PnL oficial</div><div className={`text-base ${tone(d.pnl_oficial_usd)}`}>US$ {n(d.pnl_oficial_usd)}</div>
              <div className="text-slate-500">{d.resueltas} resueltas · por US$ {n(d.pnl_por_usd_pct, 1)}%</div></div>
            <div><div className="text-slate-500">PnL con Binance al cierre</div><div className={`text-base ${tone(d.pnl_binance_usd)}`}>US$ {n(d.pnl_binance_usd)}</div>
              <div className="text-slate-500">invertido US$ {n(d.invertido_usd)}</div></div>
            <div><div className="text-slate-500">Señales / llenadas / perdidas</div><div className="text-base text-slate-100">{d.senales} / {d.llenadas} / {d.no_llenadas}</div>
              <div className="text-slate-500">{n(d.pct_no_llenadas, 0)}% se las llevó otro antes</div></div>
            <div><div className="text-slate-500">Aciertos · t por ventana</div><div className="text-base text-slate-100">{n(d.aciertos_pct, 0)}% · {n(d.t_por_ventana)}</div>
              <div className="text-slate-500">{n(d.dias, 1)} días · {d.pnl_por_dia_usd == null ? "—" : `US$ ${n(d.pnl_por_dia_usd)}/día`}</div></div>
          </div>
          {crit && (
            <div className={crit.cumple ? "text-emerald-400" : "text-amber-300"}>
              Criterio para plata real ({crit.texto}): {crit.cumple ? "CUMPLE" : `todavía no (${d.resueltas}/${crit.min_resueltas} resueltas)`}
            </div>
          )}
          <table className="w-full">
            <thead><tr className="text-slate-500 text-left">
              <th className="py-1">Hora</th><th>Mercado</th><th>Lado</th><th>Precio</th><th>US$</th><th>Ventaja</th><th>PnL Binance</th><th>PnL oficial</th>
            </tr></thead>
            <tbody>
              {ult.map((u: any) => (
                <tr key={u.mercado} className="border-t border-slate-800/60">
                  <td className="py-1 text-slate-400">{hora(u.t)}</td><td className="text-slate-300">{u.mercado}</td>
                  <td className={u.lado === "up" ? "text-emerald-300" : "text-rose-300"}>{u.lado === "up" ? "sube" : "baja"}</td>
                  <td>{n(u.precio, 3)}</td><td>{n(u.usd)}</td><td>{u.edge == null ? "—" : `${n(u.edge * 100, 1)} pts`}</td>
                  <td className={tone(u.pnl_binance)}>{n(u.pnl_binance)}</td><td className={tone(u.pnl_oficial)}>{n(u.pnl_oficial)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
