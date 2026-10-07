"""Paper en vivo de Polymarket up/down contra Binance (lee data/paper/poly_updown/)."""
import json
import time

from fastapi import APIRouter

router = APIRouter(prefix="/api/research", tags=["Research"])


@router.get("/poly_paper")
def poly_paper_status():
    import src.paper.poly_updown_paper as pp
    state = {}
    p = pp.OUT_DIR / "state.json"
    if p.exists():
        try:
            state = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            state = {}
    age = time.time() - p.stat().st_mtime if p.exists() else None
    return {"corriendo": age is not None and age < 120, "actualizado_hace_s": age,
            "config": state.get("config"), "abiertas": state.get("abiertas") or [],
            **pp.summarize_events(pp.load_events())}
