import React, { useEffect, useState } from "react";
import { Users } from "lucide-react";

/** Canonical pump.fun forward paper: WALLET_SKILL_V1. Older group/niche experiments are archived/read-only. */
export function PumpPaperPanel() {
  const api = process.env.NEXT_PUBLIC_API_URL || "";
  const [d, setD] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(api + "/api/research/pump_paper");
        const h = await fetch(api + "/api/research/runtime_health");
        if (h.ok) setHealth((await h.json()).components?.pumpfun_paper || null);
        if (r.ok) { setD(await r.json()); setErr(""); }
        else setErr("El backend respondió " + r.status);
      } catch {
        setErr("No me puedo comunicar con el backend.");
      }
    };
    poll();
    const t = setInterval(poll, 10000);
    return () => clearInterval(t);
  }, []);

  const n = (x: any, dec = 2) => (x === null || x === undefined ? "—" : Number(x).toFixed(dec));
  const tone = (x: any) => (x === null || x === undefined ? "text-slate-400" : x >= 0 ? "text-emerald-400" : "text-rose-400");
  const cuentas: any[] = d?.cuentas || [];
  const archivadas: any[] = d?.archivadas || [];
  const ws = d?.wallet_skill || {};
  const status = health?.status || "NEVER_STARTED";

  return (
    <div className="rounded-lg border border-fuchsia-900/60 bg-slate-950/40 p-4 text-xs font-mono-code space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className={status === "RUNNING" ? "text-emerald-400" : "text-amber-300"}>{status}</span>
        <Users className="w-4 h-4 text-fuchsia-400" />
        <span className="text-slate-100 font-semibold">pump.fun — WALLET_SKILL_V1</span>
        <span className="text-slate-500">paper forward · 20 SOL · 0,5 SOL fijo · máx 30 · buyer #10 · entrada en trade siguiente</span>
        {err && <span className="text-rose-300">{err}</span>}
      </div>

      <div className="border border-emerald-900/40 rounded p-3">
        <div className="text-emerald-300 font-semibold mb-2">ACTIVE RESEARCH — NO VALIDADO</div>
        <div className="grid md:grid-cols-4 gap-2 text-slate-400 mb-3">
          <div>Good wallets: <span className="text-slate-100">{ws.good_wallets_current ?? "—"}</span></div>
          <div>Regla: <span className="text-slate-100">≥5 maduras / ≥35% hit 2x</span></div>
          <div>Crédito: <span className="text-slate-100">diferido 2h</span></div>
          <div>Economía: <span className="text-amber-300">{d?.fee_model?.status || "—"}</span></div>
        </div>
        <table className="w-full">
          <thead><tr className="text-slate-500 text-left">
            <th>Cuenta</th><th>Capital</th><th>Resultado</th><th>Abiertas</th><th>Cerradas</th><th>Hit 2x</th><th>Señales</th><th>Fees</th>
          </tr></thead>
          <tbody>
            {cuentas.map((c) => (
              <tr key={c.cuenta} className="border-t border-slate-800/60">
                <td className="py-1 text-slate-100">{c.cuenta === "wallet_ladder_v1" ? "Wallet Skill V1" : "Control aleatorio"}</td>
                <td>{n(c.equity_sol, 3)} SOL</td>
                <td className={tone(c.resultado_pct)}>{c.resultado_pct === null ? "—" : (c.resultado_pct >= 0 ? "+" : "") + n(c.resultado_pct) + "%"}</td>
                <td>{c.abiertas}</td><td>{c.cerradas}</td><td>{c.hit_2x}</td><td>{c.senales}</td><td>{n(c.comisiones_sol, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className="border border-slate-800 rounded p-3">
        <summary className="cursor-pointer text-slate-300 font-semibold">Experimentos archivados — read only</summary>
        <table className="w-full mt-2">
          <thead><tr className="text-slate-500 text-left"><th>Cuenta</th><th>Estado</th><th>Resultado histórico</th><th>Cerradas</th><th>Señales</th></tr></thead>
          <tbody>
            {archivadas.map((a) => (
              <tr key={a.cuenta} className="border-t border-slate-800/60">
                <td className="py-1 text-slate-400">{a.cuenta}</td>
                <td className="text-rose-300">{a.status}</td>
                <td className={tone(a.resultado_pct)}>{a.resultado_pct === undefined ? "—" : n(a.resultado_pct) + "%"}</td>
                <td>{a.cerradas ?? "—"}</td><td>{a.senales ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
