import React, { useEffect, useRef, useState } from "react";
import { Download, RefreshCw } from "lucide-react";
import { Card } from "../common/Card";

export function HistoryPanel() {
  const api = process.env.NEXT_PUBLIC_API_URL || "";
  const [st, setSt] = useState<any>(null);
  const [months, setMonths] = useState(12);
  const timer = useRef<any>(null);

  const poll = async () => {
    try {
      const r = await fetch(`${api}/api/history/status`);
      if (!r.ok) { setSt({ state: "ERROR", message: "El backend todavía no tiene esta función: esperá unos segundos y apretá F5." }); return; }
      setSt(await r.json());
    } catch { setSt({ state: "ERROR", message: "No me puedo comunicar con el backend." }); }
  };

  useEffect(() => { poll(); timer.current = setInterval(poll, 3000); return () => clearInterval(timer.current); }, []);

  const start = async () => {
    try {
      const r = await fetch(`${api}/api/history/download?months=${months}`, { method: "POST" });
      if (!r.ok) { setSt({ ...(st || {}), state: "ERROR", message: `El backend respondió con error ${r.status}.` }); return; }
    } catch { setSt({ ...(st || {}), state: "ERROR", message: "No me puedo comunicar con el backend." }); return; }
    poll();
  };

  const running = st?.state === "RUNNING";
  const p = st?.progress;
  const pctDone = p && p.total ? Math.round((p.done / p.total) * 100) : 0;
  const inv = st?.inventory || {};

  return (
    <Card title="Historial de Binance (gratis)" subtitle="Velas de 1 minuto de los futuros de Binance, para probar estrategias con meses de datos sin esperar al recorder" variant="terminal">
      <div className="space-y-3 text-xs font-mono-code text-slate-300">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-slate-400">Meses a descargar:</label>
          <select value={months} onChange={(e) => setMonths(Number(e.target.value))} className="bg-slate-900 border border-slate-700 rounded px-2 py-1">
            {[3, 6, 12, 24].map((m) => (<option key={m} value={m}>{m}</option>))}
          </select>
          <button disabled={running} onClick={start} className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-sky-900/60 hover:bg-sky-800 border border-sky-700 text-sky-100 disabled:opacity-50">
            <Download className="w-3.5 h-3.5" /> {running ? "Descargando..." : "Descargar historial"}
          </button>
          <button onClick={poll} className="flex items-center gap-1.5 px-2 py-1.5 rounded bg-slate-800 border border-slate-700"><RefreshCw className="w-3.5 h-3.5" /></button>
        </div>

        {running && (
          <div>
            <div className="h-2 rounded bg-slate-800 overflow-hidden"><div className="h-2 bg-sky-500" style={{ width: `${pctDone}%` }} /></div>
            <div className="text-slate-400 mt-1">{pctDone}% · {st?.message}</div>
          </div>
        )}
        {!running && st?.message && <div className={st.state === "ERROR" ? "text-rose-300" : "text-slate-300"}>{st.message}</div>}

        <div className="text-slate-400">
          En tu PC: <span className="text-slate-100">{st?.symbols_on_disk ?? 0} criptos</span>
          {st?.first_period ? <> · desde <span className="text-slate-100">{st.first_period}</span> hasta <span className="text-slate-100">{st.last_period}</span></> : null}
          {" "}· {st?.size_mb ?? 0} MB. Se puede volver a apretar cuando quieras: solo baja lo que falta.
        </div>
        {Object.keys(inv).length > 0 && (
          <details>
            <summary className="cursor-pointer text-slate-400">Ver detalle por cripto</summary>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-1 mt-2">
              {Object.entries(inv).map(([s, v]: any) => (
                <div key={s} className="px-2 py-1 rounded bg-slate-900 border border-slate-800">{s}: {v.first} → {v.last}</div>
              ))}
            </div>
          </details>
        )}
      </div>
    </Card>
  );
}
