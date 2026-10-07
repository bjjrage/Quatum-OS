"""Snapshot liviano del OS (unos KB) para que el estado se pueda leer desde GitHub sin capturas.

    uv run python scripts/os_snapshot.py              # escribe data/runtime/snapshot/latest.md y .json (local)
    uv run python scripts/os_snapshot.py --push       # además lo sube a la rama `snapshots` de origin

Qué incluye: resumen del paper de Polymarket (+ últimos 30 eventos), cada data/paper/*/state.json recortado (números
y listas cortas), salud de componentes, últimas líneas WARNING/ERROR de data/runtime/logs (con claves tapadas) y
actividad de cada tabla del recorder en la última hora.
Qué NO incluye: .env, sesiones, claves, parquets, texto de mensajes de Telegram.

--push NO toca la carpeta de trabajo ni la rama actual: arma el commit con git hash-object/mktree/commit-tree sobre el
último `origin/snapshots` y hace `git push origin <commit>:refs/heads/snapshots`.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = ROOT / "data" / "runtime" / "snapshot"
SECRET_RE = re.compile(r"(?i)(api[-_]?key=|apikey=|token=|secret=|password=|authorization:\s*bearer\s+)[^\s&\"',]+")
LONG_SECRET_RE = re.compile(r"\b(sk|xai|ghp|gho|pk)[-_][A-Za-z0-9_\-]{16,}\b")
SKIP_KEYS = {"text", "accounts_json", "summary", "description", "raw_json"}


def redact(s: str) -> str:
    return LONG_SECRET_RE.sub("[CLAVE]", SECRET_RE.sub(lambda m: m.group(1) + "[CLAVE]", s))


def trim(x: Any, depth: int = 0, max_list: int = 12) -> Any:
    """Recorta estructuras grandes: listas a sus últimos `max_list`, textos largos, sin campos de texto libre."""
    if isinstance(x, dict):
        if depth > 4:
            return f"<{len(x)} claves>"
        return {k: trim(v, depth + 1, max_list) for k, v in list(x.items())[:60] if k not in SKIP_KEYS}
    if isinstance(x, list):
        tail = x[-max_list:]
        out = [trim(v, depth + 1, max_list) for v in tail]
        return out if len(x) <= max_list else [f"... {len(x) - max_list} anteriores"] + out
    if isinstance(x, str):
        return redact(x[:200])
    return x


def paper_states(root: Path) -> Dict[str, Any]:
    out = {}
    for p in sorted((root / "data" / "paper").glob("*/state.json")):
        try:
            out[p.parent.name] = {"actualizado_hace_min": round((time.time() - p.stat().st_mtime) / 60, 1),
                                  "estado": trim(json.loads(p.read_text(encoding="utf-8")))}
        except (OSError, ValueError) as e:
            out[p.parent.name] = {"error": f"{type(e).__name__}"}
    return out


def poly_summary(root: Path) -> Dict[str, Any]:
    try:
        import src.paper.poly_updown_paper as pp
        pp.OUT_DIR = root / "data" / "paper" / "poly_updown"
        ev = pp.load_events()
        s = pp.summarize_events(ev, recent=30)
        s["ultimos_eventos"] = [trim(e) for e in ev[-30:]]
        return s
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:120]}"}


def health(root: Path) -> Dict[str, Any]:
    try:
        from src.common.runtime_health import runtime_health_snapshot
        comps = runtime_health_snapshot(root).get("components", {})
        return {k: {kk: v.get(kk) for kk in ("status", "pid", "last_error", "error", "updated_at") if v.get(kk) is not None}
                for k, v in comps.items()}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:120]}"}


def log_problems(root: Path, per_file: int = 20) -> Dict[str, List[str]]:
    out = {}
    for p in sorted((root / "data" / "runtime" / "logs").glob("*.log")):
        try:
            with open(p, "rb") as fh:
                fh.seek(max(0, p.stat().st_size - 2_000_000))
                lines = fh.read().decode("utf-8", errors="replace").splitlines()
        except OSError:
            continue
        bad = [redact(ln[:300]) for ln in lines if '"WARNING"' in ln or '"ERROR"' in ln or "Traceback" in ln]
        if bad:
            out[p.name] = bad[-per_file:]
    return out


def recorder_activity(root: Path, window_s: int = 3600) -> Dict[str, Any]:
    now, out = time.time(), {}
    raw = root / "data" / "raw"
    if not raw.exists():
        return out
    for venue in sorted(d for d in raw.iterdir() if d.is_dir() and d.name not in ("quarantine", ".tmp")):
        for table in sorted(d for d in venue.iterdir() if d.is_dir() and d.name.startswith("table=")):
            n_recent, last = 0, 0.0
            for dirpath, _, files in os.walk(table):
                for f in files:
                    if f.endswith(".parquet"):
                        m = os.stat(os.path.join(dirpath, f)).st_mtime
                        last = max(last, m)
                        n_recent += m >= now - window_s
            out[f"{venue.name}/{table.name[6:]}"] = {"archivos_ultima_hora": n_recent,
                                                      "ultima_escritura_hace_min": round((now - last) / 60, 1) if last else None}
    return out


def to_markdown(snap: Dict[str, Any]) -> str:
    p = snap["polymarket"]
    lines = [f"# Snapshot Quant OS — {snap['generado_utc']}", "", "## Polymarket up/down (paper)", ""]
    if "error" in p:
        lines.append(f"- error: {p['error']}")
    else:
        lines += [f"- Señales {p['senales']} · llenadas {p['llenadas']} · perdidas {p['no_llenadas']} "
                  f"({p['pct_no_llenadas'] or 0:.0f}% se las llevó otro)",
                  f"- PnL Binance US$ {p['pnl_binance_usd']:.2f} · PnL oficial US$ {p['pnl_oficial_usd']:.2f} "
                  f"({p['resueltas']} resueltas) · aciertos {p['aciertos_pct'] or 0:.0f}% · t por ventana {p['t_por_ventana']}",
                  f"- Criterio: {'CUMPLE' if p['criterio']['cumple'] else 'todavía no'}"]
    lines += ["", "## Salud", ""] + [f"- {k}: {v.get('status', v)}" for k, v in snap["salud"].items()]
    lines += ["", "## Papers (state.json)", ""] + [f"- {k}: actualizado hace {v.get('actualizado_hace_min')} min"
                                                   for k, v in snap["papers"].items()]
    lines += ["", "## Recorders (última hora)", "", "| tabla | archivos | última escritura (min) |", "|---|---|---|"]
    lines += [f"| {k} | {v['archivos_ultima_hora']} | {v['ultima_escritura_hace_min']} |" for k, v in snap["recorders"].items()]
    lines += ["", "## Problemas en logs (últimos)", ""]
    for f, ls in snap["logs"].items():
        lines += [f"### {f}", "```"] + ls[-8:] + ["```"]
    lines += ["", "Detalle completo en latest.json."]
    return "\n".join(lines)


def build(root: Path = ROOT) -> Dict[str, Any]:
    return {"generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "polymarket": poly_summary(root),
            "papers": paper_states(root), "salud": health(root), "recorders": recorder_activity(root),
            "logs": log_problems(root)}


def git(*args: str, input_text: str = None, check: bool = True) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": os.environ.get("GIT_AUTHOR_NAME", "Quant OS snapshot"),
           "GIT_AUTHOR_EMAIL": os.environ.get("GIT_AUTHOR_EMAIL", "snapshot@quant-os.local"),
           "GIT_COMMITTER_NAME": os.environ.get("GIT_COMMITTER_NAME", "Quant OS snapshot"),
           "GIT_COMMITTER_EMAIL": os.environ.get("GIT_COMMITTER_EMAIL", "snapshot@quant-os.local")}
    r = subprocess.run(["git", *args], cwd=ROOT, input=input_text, capture_output=True, text=True,
                       encoding="utf-8", env=env)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {args[0]} falló: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def push(files: Dict[str, str]) -> str:
    git("fetch", "-q", "origin", "snapshots", check=False)
    parent = git("rev-parse", "--verify", "-q", "refs/remotes/origin/snapshots", check=False)
    entries = []
    for name, content in files.items():
        sha = git("hash-object", "-w", "--stdin", input_text=content)
        entries.append(f"100644 blob {sha}\t{name}")
    tree = git("mktree", input_text="\n".join(entries) + "\n")
    args = ["commit-tree", tree, "-m", f"snapshot {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"]
    if parent:
        args[2:2] = ["-p", parent]
    commit = git(*args)
    git("push", "-q", "origin", f"{commit}:refs/heads/snapshots")
    return commit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()
    snap = build()
    js = json.dumps(snap, indent=1, ensure_ascii=False, default=str)
    md = to_markdown(snap)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_text(js, encoding="utf-8")
    (OUT / "latest.md").write_text(md, encoding="utf-8")
    print(f"Snapshot: {len(js) / 1024:.1f} KB en {OUT}")
    if a.push:
        print(f"Subido a origin/snapshots: {push({'latest.json': js, 'latest.md': md})}")


if __name__ == "__main__":
    main()
