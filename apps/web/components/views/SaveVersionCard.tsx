import React, { useEffect, useRef, useState } from "react";
import { GitCommit } from "lucide-react";

/** "Guardar versión": runs the tests on this PC and, only if they pass, commits and pushes to GitHub. */
export function SaveVersionCard() {
  const api = process.env.NEXT_PUBLIC_API_URL || "";
  const [st, setSt] = useState<any>(null);
  const [note, setNote] = useState("");
  const timer = useRef<any>(null);

  const poll = async () => {
    try {
      const r = await fetch(`${api}/api/system/git/save/status`);
      if (r.ok) setSt(await r.json());
    } catch { /* backend restarting */ }
  };
  useEffect(() => { poll(); timer.current = setInterval(poll, 3000); return () => clearInterval(timer.current); }, []);

  const save = async () => {
    const msg = note.trim() ? `Quant OS: ${note.trim()}` : "Quant OS: guardar versión";
    try {
      const r = await fetch(`${api}/api/system/git/save?message=${encodeURIComponent(msg)}&push=true`, { method: "POST" });
      if (!r.ok) setSt({ state: "ERROR", message: `El backend respondió con error ${r.status}.` });
    } catch { setSt({ state: "ERROR", message: "No me puedo comunicar con el backend." }); }
    poll();
  };

  const running = st?.state === "RUNNING";
  const color = st?.state === "DONE" ? "text-emerald-300" : st?.state === "ERROR" ? "text-rose-300" : "text-slate-400";

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-xs font-mono-code">
      <div className="flex flex-wrap items-center gap-3">
        <GitCommit className="w-4 h-4 text-cyan-400" />
        <span className="text-slate-100 font-semibold">Guardar versión</span>
        <span className="text-slate-500">corre los tests y, si pasan, guarda y sube a GitHub</span>
        <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="qué cambió (opcional)"
          className="flex-1 min-w-[200px] bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200" />
        <button disabled={running} onClick={save}
          className="px-3 py-1.5 rounded bg-cyan-900/60 hover:bg-cyan-800 border border-cyan-700 text-cyan-100 disabled:opacity-50">
          {running ? "Guardando..." : "Guardar versión"}
        </button>
      </div>
      {st?.message && <div className={`mt-2 ${color}`}>{st.message}</div>}
    </div>
  );
}
