import React, { useEffect, useState } from "react";
import { Rocket } from "lucide-react";

/** Paper de Binance: explota el líder de un segmento -> rezagadas, con y sin filtro de X, contra el azar. */
export function LiderPaperPanel() {
  const api = process.env.NEXT_PUBLIC_API_URL || "";
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${api}/api/research/lider_paper`);
        if (r.ok) { setD(await r.json()); setErr(""); } else setErr(`El backend respondió ${r.status}`);
      } catch { setErr("No me puedo comunicar con el backend."); }
    };
    poll();
    const t = setInterval(poll, 30000);
    return () => clearInterval(t);
  }, []);
  const n = (x: any, dec = 2) => (x === null || x === undefined ? "—" : Number(x).toFixed(dec));
  const tone = (x: any) => (x === null || x === undefined ? "text-slate-400" : x >= 0 ? "text-emerald-400" : "text-rose-400");
  const cuentas: any[] = d?.cuentas || [];
  const eventos: any[] = d?.eventos || [];
  const runtimeHealth = d?.runtime || {};
  const runtimeStatus = runtimeHealth.status || "NEVER_STARTED";
  const runtimeLabel: Record<string, string> = { NEVER_STARTED: "Proceso apagado", STARTING: "Proceso iniciando", RUNNING: cuentas.length || eventos.length ? "Proceso activo" : "Proceso activo sin eventos", DEGRADED: "Proceso degradado", ERROR: "Proceso con error", DISABLED: "Proceso deshabilitado", STOPPED: "Proceso apagado" };
  const sym = (s: string) => s.replace("USDT", "");
  return (
    <div className="rounded-lg border border-cyan-900/60 bg-slate-950/40 p-4 text-xs font-mono-code space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className={runtimeStatus === "RUNNING" ? "text-emerald-400" : runtimeStatus === "ERROR" || runtimeStatus === "DEGRADED" ? "text-rose-300" : "text-amber-300"}>{runtimeLabel[runtimeStatus] || runtimeStatus}</span>
        <Rocket className="w-4 h-4 text-cyan-400" />
        <span className="text-slate-100 font-semibold">Binance — explotó el líder del segmento, ¿siguen las rezagadas?</span>
        <span className="text-slate-500">1 chequeo por día · 1.000 USD por evento · 7 días · X filtra (tope diario de gasto)</span>
        {err && <span className="text-rose-300">{err}</span>}
      </div>
      {!cuentas.length ? (
        <div className="text-slate-400">{runtimeStatus === "RUNNING" ? "Proceso activo sin eventos." : runtimeStatus === "STARTING" ? "Proceso iniciando." : runtimeStatus === "ERROR" || runtimeStatus === "DEGRADED" ? (runtimeHealth?.last_error_type || "Error") + ": " + (runtimeHealth?.last_error_message_sanitized || "ver estado local") : runtimeLabel[runtimeStatus] || runtimeStatus}</div>
      ) : (
        <table className="w-full">
          <thead><tr className="text-slate-500 text-left">
            <th className="py-1">Cuenta</th><th>Equity (USD)</th><th>Resultado</th><th>Abiertas</th><th>Cerradas</th>
            <th>Exceso vs mercado</th><th>Aciertos</th><th>Costos</th>
          </tr></thead>
          <tbody>
            {cuentas.map((c) => (
              <tr key={c.cuenta} className="border-t border-slate-800/60">
                <td className="py-1 text-slate-100">{c.descripcion}</td>
                <td className="text-slate-200">{n(c.equity, 0)}</td>
                <td className={tone(c.resultado_pct)}>{`${c.resultado_pct >= 0 ? "+" : ""}${n(c.resultado_pct)}%`}</td>
                <td className="text-slate-400">{c.abiertas}</td>
                <td className="text-slate-400">{c.cerradas}</td>
                <td className={tone(c.exceso_medio_pct)}>{c.exceso_medio_pct === null ? "—" : `${n(c.exceso_medio_pct)}%`}</td>
                <td className="text-slate-400">{c.aciertos_pct === null ? "—" : `${n(c.aciertos_pct, 0)}%`}</td>
                <td className="text-slate-400">{n(c.costos, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="text-slate-500">
        Último chequeo: {d?.ultimo_chequeo || "—"} · Gasto en X hoy: US$ {n(d?.gasto_x_hoy, 2)} · total: US$ {n(d?.gasto_x_total, 2)}
      </div>
      {eventos.length > 0 && (
        <div>
          <div className="text-slate-300 font-semibold mb-1">Últimos eventos</div>
          {eventos.map((e) => (
            <div key={e.dia + e.segmento} className="border-t border-slate-800/60 py-1">
              <span className="text-slate-100">{e.dia} · {e.segmento}</span>
              <span className="text-orange-400"> líder {sym(e.lideres[0].symbol)} +{n(e.lideres[0].r3 * 100, 0)}%</span>
              <span className="text-slate-400"> · rezagadas: </span>
              {e.rezagadas.map((r: any) => (
                <span key={r.symbol} className={r.x?.x_status === "X_POSITIVE" && r.x.posts_found >= 5 && r.x.narrative_link ? "text-emerald-400" : "text-slate-500"}>
                  {sym(r.symbol)}{r.x ? ` (X ${r.x.x_status || "NO_DATA"}${r.x.posts_found === null || r.x.posts_found === undefined ? "" : `: ${r.x.posts_found}`})` : " (X: NO_DATA)"}{" "}
                </span>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
