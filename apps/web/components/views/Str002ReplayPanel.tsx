import React, { useEffect, useRef, useState } from "react";
import { Play, RefreshCw } from "lucide-react";
import { Card } from "../common/Card";

const NAMES: Record<string, string> = {
  A_actual: "A · Diseño actual",
  B_marcelo: "B · Estilo Marcelo",
  C_intermedia: "C · Intermedia",
  D_marcelo_5m: "D · Estilo Marcelo, velas de 5 min",
};

const VERDICT: Record<string, [string, string]> = {
  MEJOR_QUE_AZAR: ["Le gana al azar", "bg-emerald-950/50 text-emerald-300 border-emerald-800"],
  IGUAL_QUE_AZAR: ["No se distingue del azar", "bg-amber-950/40 text-amber-300 border-amber-800"],
  PEOR_QUE_AZAR: ["Peor que el azar", "bg-rose-950/40 text-rose-300 border-rose-800"],
};

const PROP_STYLE: Record<string, string> = {
  PASA: "bg-emerald-950/50 text-emerald-300 border-emerald-800",
  AUN_NO: "bg-amber-950/40 text-amber-300 border-amber-800",
  SIN_DATOS: "bg-slate-900 text-slate-500 border-slate-700",
  FAIL_DAILY: "bg-rose-950/40 text-rose-300 border-rose-800",
  FAIL_MAX: "bg-rose-950/40 text-rose-300 border-rose-800",
  FAIL_RULES: "bg-rose-950/40 text-rose-300 border-rose-800",
};
const PROP_TEXT: Record<string, string> = {
  PASA: "Pasa",
  AUN_NO: "Todavía no",
  SIN_DATOS: "Sin datos",
  FAIL_DAILY: "No pasa: pérdida diaria",
  FAIL_MAX: "No pasa: pérdida total",
  FAIL_RULES: "No permitido",
};

const TH = "px-3 py-2 font-normal text-slate-400 align-bottom";
const TD = "px-3 py-2 align-top";
const TDN = "px-3 py-2 text-right tabular-nums align-top";

const signColor = (v: any) => (typeof v === "number" ? (v > 0 ? "text-emerald-300" : v < 0 ? "text-rose-300" : "") : "");

function ResultTable({ rows, label }: { rows: [string, any][]; label: (k: string, v: any) => string }) {
  return (
    <div className="overflow-x-auto rounded border border-slate-800">
      <table className="w-full text-left">
        <thead className="bg-slate-900/60">
          <tr>
            <th className={TH}>Versión</th>
            <th className={TH + " text-right"}>Operaciones<br /><span className="text-slate-500">(por día)</span></th>
            <th className={TH + " text-right"}>Ganadoras</th>
            <th className={TH + " text-right"}>Resultado por operación<br /><span className="text-slate-500">antes de comisiones</span></th>
            <th className={TH + " text-right"}>Resultado por operación<br /><span className="text-slate-500">después de comisiones</span></th>
            <th className={TH + " text-right"}>Suma de todas<br /><span className="text-slate-500">las operaciones</span></th>
            <th className={TH + " text-right"}>Peor caída<br /><span className="text-slate-500">acumulada</span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([k, v]) => {
            const s = v.summary || {};
            return (
              <tr key={k} className="border-t border-slate-800">
                <td className={TD + " text-slate-100 whitespace-nowrap"}>{label(k, v)}</td>
                <td className={TDN}>{s.n_trades ?? 0} <span className="text-slate-500">({num(s.trades_per_day)})</span></td>
                <td className={TDN}>{typeof s.win_rate === "number" ? `${(s.win_rate * 100).toFixed(0)}%` : "—"}</td>
                <td className={TDN + " " + signColor(s.mean_gross_pct)}>{pct(s.mean_gross_pct)}</td>
                <td className={TDN + " " + signColor(s.mean_net_pct)}>{pct(s.mean_net_pct)}</td>
                <td className={TDN + " " + signColor(s.sum_net_pct)}>{pct(s.sum_net_pct)}</td>
                <td className={TDN + " text-rose-300"}>{typeof s.max_drawdown_pct_points === "number" ? `-${pct(s.max_drawdown_pct_points)}` : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function BaselineTable({ base }: { base: Record<string, any> }) {
  const rows = Object.entries(base || {});
  if (!rows.length) return null;
  return (
    <div className="overflow-x-auto rounded border border-slate-800">
      <table className="w-full text-left">
        <thead className="bg-slate-900/60">
          <tr>
            <th className={TH}>Versión</th>
            <th className={TH + " text-right"}>La estrategia<br /><span className="text-slate-500">por operación</span></th>
            <th className={TH + " text-right"}>Entrando al azar<br /><span className="text-slate-500">resultado típico</span></th>
            <th className={TH + " text-right"}>Al azar, rango normal<br /><span className="text-slate-500">(9 de cada 10 veces)</span></th>
            <th className={TH + " text-right"}>Veces que el azar<br /><span className="text-slate-500">le fue peor</span></th>
            <th className={TH}>Conclusión</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([k, b]) => {
            if (b.status !== "OK") {
              return (<tr key={k} className="border-t border-slate-800"><td className={TD + " text-slate-100"}>{NAMES[k] || k}</td><td className={TD} colSpan={5}>{b.reason || "Sin datos"}</td></tr>);
            }
            const v = VERDICT[b.verdict] || ["—", ""];
            return (
              <tr key={k} className="border-t border-slate-800">
                <td className={TD + " text-slate-100 whitespace-nowrap"}>{NAMES[k] || k}</td>
                <td className={TDN + " " + signColor(b.strategy_mean_net_pct)}>{pct(b.strategy_mean_net_pct)}</td>
                <td className={TDN + " " + signColor(b.random_median_net_pct)}>{pct(b.random_median_net_pct)}</td>
                <td className={TDN}>{pct(b.random_p5_net_pct)} a {pct(b.random_p95_net_pct)}</td>
                <td className={TDN}>{typeof b.share_random_worse === "number" ? `${(b.share_random_worse * 100).toFixed(0)}%` : "—"}</td>
                <td className={TD}><span className={`inline-block px-2 py-0.5 rounded border ${v[1]}`}>{v[0]}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ExamTable({ rows, label }: { rows: [string, any][]; label: (k: string, v: any) => string }) {
  const firms = rows.length ? Object.keys(rows[0][1].prop_check || {}) : [];
  if (!firms.length) return null;
  return (
    <div className="overflow-x-auto rounded border border-slate-800">
      <table className="w-full text-left">
        <thead className="bg-slate-900/60">
          <tr>
            <th className={TH}>Versión</th>
            {firms.map((f) => (<th key={f} className={TH}>{rows[0][1].prop_check[f].label}</th>))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k} className="border-t border-slate-800">
              <td className={TD + " text-slate-100 whitespace-nowrap"}>{label(k, v)}</td>
              {firms.map((f) => {
                const c = v.prop_check?.[f];
                if (!c) return <td key={f} className={TD}>—</td>;
                const detail = c.status === "AUN_NO" && typeof c.progress_pct === "number"
                  ? `va ${c.progress_pct >= 0 ? "+" : ""}${c.progress_pct.toFixed(1)}% · objetivo ${c.target_pct}%`
                  : c.status === "PASA" ? "llegó al objetivo" : "";
                return (
                  <td key={f} className={TD} title={c.reason}>
                    <span className={`inline-block px-2 py-0.5 rounded border ${PROP_STYLE[c.status] || ""}`}>{PROP_TEXT[c.status] || c.status}</span>
                    {detail && <div className="text-slate-500 mt-1">{detail}</div>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const pct = (v: any) => (typeof v === "number" && isFinite(v) ? `${v.toFixed(2)}%` : "—");
const num = (v: any, d = 1) => (typeof v === "number" && isFinite(v) ? v.toFixed(d) : "—");

export function Str002ReplayPanel() {
  const api = process.env.NEXT_PUBLIC_API_URL || "";
  const [days, setDays] = useState(7);
  const [source, setSource] = useState<"recorded" | "history">("recorded");
  const [st, setSt] = useState<any>(null);
  const timer = useRef<any>(null);

  const poll = async () => {
    try {
      const r = await fetch(`${api}/api/backtests/str002/status`);
      if (!r.ok) {
        setSt({ state: "ERROR", message: "El backend no tiene esta función todavía: cerrá la ventana 'Quant OS - Backend API' y abrí start.bat de nuevo." });
        return;
      }
      setSt(await r.json());
    } catch {
      setSt({ state: "ERROR", message: "No me puedo comunicar con el backend." });
    }
  };

  useEffect(() => {
    poll();
    timer.current = setInterval(poll, 3000);
    return () => clearInterval(timer.current);
  }, []);

  const run = async () => {
    try {
      const r = await fetch(`${api}/api/backtests/str002/run?days=${days}&source=${source}`, { method: "POST" });
      if (!r.ok) {
        setSt({ state: "ERROR", message: r.status === 404
          ? "El backend no tiene esta función todavía: cerrá la ventana 'Quant OS - Backend API' y abrí start.bat de nuevo."
          : `El backend respondió con error ${r.status}.` });
        return;
      }
    } catch {
      setSt({ state: "ERROR", message: "No me puedo comunicar con el backend." });
      return;
    }
    poll();
  };

  const running = st?.state === "RUNNING";
  const result = st?.result;
  const counts = result?.impulse_counts?.impulses_per_day;

  return (
    <Card title="STR-002 · Prueba sobre tus datos grabados" subtitle="Impulso → primera frenada → entrada long → salida con trailing stop" variant="terminal">
      <div className="space-y-4 text-xs font-mono-code text-slate-300">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-slate-400">Datos:</label>
          <select value={source} onChange={(e) => setSource(e.target.value as any)} className="bg-slate-900 border border-slate-700 rounded px-2 py-1">
            <option value="recorded">Grabados por el recorder</option>
            <option value="history">Historial de Binance</option>
          </select>
          <label className="text-slate-400">Últimos días:</label>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="bg-slate-900 border border-slate-700 rounded px-2 py-1">
            {[1, 3, 7, 14, 30, 60, 90, 180].map((d) => (<option key={d} value={d}>{d}</option>))}
          </select>
          <button disabled={running} onClick={run} className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-900/60 hover:bg-emerald-800 border border-emerald-700 text-emerald-100 disabled:opacity-50">
            <Play className="w-3.5 h-3.5" /> {running ? "Corriendo..." : "Correr prueba"}
          </button>
          <button onClick={poll} className="flex items-center gap-1.5 px-2 py-1.5 rounded bg-slate-800 border border-slate-700">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="text-slate-400">{st?.message || "—"}</div>

        {result && (
          <>
            <div className="p-2 rounded bg-amber-950/20 border border-amber-900/40 text-amber-200">
              {result.source === "history" ? "Historial de Binance (sin libro de órdenes: se entra al cierre de la vela + deslizamiento). " : "Datos grabados por el recorder. "}
              Prueba exploratoria sobre {num(result.span_days, 2)} días y {result.n_alts} criptos. Se comparan varias versiones sobre los mismos datos: sirve para descartar o elegir candidatas, no prueba que haya ganancia.
            </div>
            {result.coverage && (
              <div className={result.coverage.longest_continuous_hours < (result.needed_continuous_hours || 4.1)
                ? "p-2 rounded bg-rose-950/20 border border-rose-900/40 text-rose-200"
                : "p-2 rounded bg-slate-900 border border-slate-700 text-slate-300"}>
                Datos usables: {num(result.coverage.usable_minutes / 60)} h · tramo continuo más largo: {num(result.coverage.longest_continuous_hours)} h · {result.source === "history" ? "huecos sin datos" : "recorder apagado"}: {num(result.coverage.recorder_down_minutes / 60)} h.
                {" "}La estrategia necesita {num(result.needed_continuous_hours || 4.1)} h seguidas de datos antes de poder detectar un impulso
                {result.coverage.longest_continuous_hours < (result.needed_continuous_hours || 4.1) ? (result.source === "history" ? ": no alcanza; elegí más días." : ": todavía no alcanza, por eso no hay entradas. Dejá el recorder prendido sin cortes.") : "."}
              </div>
            )}

            {Object.values(result.variants || {}).some((v: any) => v.summary?.warning) && (
              <div className="text-amber-300">Hay menos de 30 operaciones por versión: los números todavía pueden ser casualidad.</div>
            )}

            <div className="text-slate-100 font-semibold pt-1">1. ¿Qué forma de ENTRAR funciona mejor?</div>
            <div className="text-slate-500 -mt-2">Todas salen igual (trailing). Solo cambia cuándo entran.</div>
            <ResultTable rows={Object.entries(result.variants || {})} label={(k) => NAMES[k] || k} />

            {result.exit_comparison && Object.keys(result.exit_comparison).length > 0 && (
              <>
                <div className="text-slate-100 font-semibold pt-3">2. ¿Qué forma de SALIR funciona mejor?</div>
                <div className="text-slate-500 -mt-2">Las tres usan exactamente las mismas entradas (versión B). Solo cambia cómo salen.</div>
                <ResultTable rows={Object.entries(result.exit_comparison)} label={(k, v) => v.label ? v.label.charAt(0).toUpperCase() + v.label.slice(1) : k} />
              </>
            )}

            {result.baseline && Object.keys(result.baseline).length > 0 && (
              <>
                <div className="text-slate-100 font-semibold pt-3">¿La señal sirve o da lo mismo entrar en cualquier momento?</div>
                <div className="text-slate-500 -mt-2">
                  Se repite la misma cantidad de operaciones, con la misma salida, pero entrando en momentos al azar ({result.baseline[Object.keys(result.baseline)[0]]?.runs ?? 200} veces). La estrategia solo sirve si le gana al azar en al menos 95 de cada 100 pruebas.
                </div>
                <BaselineTable base={result.baseline} />
              </>
            )}

            <div className="text-slate-100 font-semibold pt-3">3. ¿Habría pasado el examen de la prop firm?</div>
            <div className="text-slate-500 -mt-2">
              Arriesgando {num(result.risk_per_trade_pct, 2)}% de la cuenta por operación. Solo cuenta operaciones cerradas. Las reglas pueden cambiar: confirmalas antes de pagar.
            </div>
            <ExamTable
              rows={[...Object.entries(result.variants || {}), ...Object.entries(result.exit_comparison || {}).map(([k, v]: any) => [`exit_${k}`, v] as [string, any])]}
              label={(k, v) => (NAMES[k] || (v.label ? `B · ${v.label}` : k))}
            />

            {counts && (
              <div>
                <div className="text-slate-100 font-semibold pt-3">4. ¿Cuántos impulsos aparecen por día?</div>
                <div className="text-slate-500 mb-2">Contando todas las criptos juntas, antes de esperar la frenada. Filas: cuándo bloquea por BTC. Columnas: qué tan fuerte tiene que ser el impulso.</div>
                <div className="overflow-x-auto rounded border border-slate-800">
                <table className="w-full text-left">
                  <thead className="bg-slate-900/60"><tr><th className={TH}>Bloquea la entrada si BTC…</th><th className={TH + " text-right"}>Impulso fuerte (2)</th><th className={TH + " text-right"}>Más fuerte (2,5)</th><th className={TH + " text-right"}>Muy fuerte (3)</th></tr></thead>
                  <tbody>
                    {Object.entries(counts).map(([k, row]: any) => (
                      <tr key={k} className="border-t border-slate-800">
                        <td className={TD}>{k === "btc_block_99_sigma" ? "nunca bloquea" : k.replace("btc_block_", "cae más de ").replace("_sigma", " desvíos")}</td>
                        <td className={TDN}>{num(row["z_2"])}</td><td className={TDN}>{num(row["z_2.5"])}</td><td className={TDN}>{num(row["z_3"])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );
}
