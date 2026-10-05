import React, { useEffect, useState } from "react";
import { Users } from "lucide-react";

/** Paper de pump.fun: grupos que acumulan + nichos calientes, contra el detector tardío y el azar. */
export function PumpPaperPanel() {
  const api = process.env.NEXT_PUBLIC_API_URL || "";
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${api}/api/research/pump_paper`);
        if (r.ok) { setD(await r.json()); setErr(""); } else setErr(`El backend respondió ${r.status}`);
      } catch { setErr("No me puedo comunicar con el backend."); }
    };
    poll();
    const t = setInterval(poll, 10000);
    return () => clearInterval(t);
  }, []);
  const n = (x: any, dec = 2) => (x === null || x === undefined ? "—" : Number(x).toFixed(dec));
  const tone = (x: any) => (x === null || x === undefined ? "text-slate-400" : x >= 0 ? "text-emerald-400" : "text-rose-400");
  const cuentas: any[] = d?.cuentas || [];
  return (
    <div className="rounded-lg border border-fuchsia-900/60 bg-slate-950/40 p-4 text-xs font-mono-code space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <Users className="w-4 h-4 text-fuchsia-400" />
        <span className="text-slate-100 font-semibold">pump.fun en vivo — grupos que acumulan + nichos calientes</span>
        <span className="text-slate-500">SOL de mentira · 10 SOL por cuenta · 5% del capital por entrada · al 2x vende la mitad, el resto con stop móvil · comisiones reales</span>
        {err && <span className="text-rose-300">{err}</span>}
      </div>
      {!cuentas.length ? (
        <div className="text-slate-400">Arrancando (repasa lo grabado para encontrar grupos; tarda unos minutos)...</div>
      ) : (
        <>
          <div className="text-slate-400">
            Grupos detectados: <span className="text-slate-100">{d.grupos ?? "—"}</span> ({d.billeteras_en_grupos ?? "—"} billeteras)
          </div>
          <table className="w-full">
            <thead><tr className="text-slate-500 text-left">
              <th className="py-1">Cuenta</th><th>Capital (SOL)</th><th>Resultado</th><th>Abiertas</th>
              <th>Cerradas</th><th>Llegaron a 2x</th><th>Aciertos</th><th>Señales</th><th>Comisiones</th>
            </tr></thead>
            <tbody>
              {cuentas.map((c) => (
                <tr key={c.cuenta} className="border-t border-slate-800/60">
                  <td className="py-1 text-slate-100">{c.descripcion}</td>
                  <td className="text-slate-200">{n(c.equity_sol, 3)}</td>
                  <td className={tone(c.resultado_pct)}>{c.resultado_pct === null ? "—" : `${c.resultado_pct >= 0 ? "+" : ""}${n(c.resultado_pct)}%`}</td>
                  <td className="text-slate-400">{c.abiertas}</td>
                  <td className="text-slate-400">{c.cerradas}</td>
                  <td className="text-slate-400">{c.tomas_2x}</td>
                  <td className="text-slate-400">{c.aciertos_pct === null ? "—" : `${n(c.aciertos_pct, 0)}%`}</td>
                  <td className="text-slate-400">{c.senales}{c.saltadas ? ` (${c.saltadas} sin lugar)` : ""}</td>
                  <td className="text-slate-400">{n(c.comisiones_sol, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <div className="text-slate-300 font-semibold mb-1">Nichos ahora (últimos 30 min)</div>
              <table className="w-full"><tbody>
                {(d.nichos_ahora || []).map((r: any) => (
                  <tr key={r.nicho} className="border-t border-slate-800/60">
                    <td className="py-1 text-slate-100">{r.nicho.replace("cat:", "").replace("w:", "“") + (r.nicho.startsWith("w:") ? "”" : "")}</td>
                    <td className="text-slate-400">{n(r.sol_30m, 0)} SOL</td>
                    <td className="text-slate-400">{r.tokens_30m} tokens</td>
                    <td className={r.caliente ? "text-orange-400" : "text-slate-500"}>{r.caliente ? "CALIENTE" : `x${n(r.ratio, 1)}`}</td>
                  </tr>
                ))}
              </tbody></table>
            </div>
            <div>
              <div className="text-slate-300 font-semibold mb-1">Últimas señales de grupo</div>
              <table className="w-full"><tbody>
                {(d.ultimas_senales || []).slice(0, 10).map((s: any) => (
                  <tr key={s.ts + s.mint} className="border-t border-slate-800/60">
                    <td className="py-1 text-slate-100">{s.simbolo || s.mint.slice(0, 6)}</td>
                    <td className="text-slate-400">{s.billeteras_grupo} del grupo</td>
                    <td className="text-slate-400">{s.gente_en_token} en el token</td>
                    <td className="text-slate-400">{s.edad_min} min</td>
                    <td className="text-orange-400">{(s.nichos_calientes || []).join(", ")}</td>
                  </tr>
                ))}
              </tbody></table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
