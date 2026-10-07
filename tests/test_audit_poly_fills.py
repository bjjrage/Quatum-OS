import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("apf", Path(__file__).resolve().parents[1] / "scripts" / "audit_poly_fills.py")
apf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apf)


def test_classify_fills_against_recorded_book():
    assert apf.classify("up", 0.40, 0.40, 0.38, 2.0) == "real"
    assert apf.classify("up", 0.40, 0.55, 0.53, 2.0) == "fantasma"          # market had already moved
    assert apf.classify("down", 0.40, 0.62, 0.60, 2.0) == "real"            # down = 1 - up bid = 0.40
    assert apf.classify("down", 0.40, 0.47, 0.45, 2.0) == "fantasma"        # 1 - 0.45 = 0.55 > 0.41
    assert apf.classify("up", 0.40, 0.40, 0.38, 60.0) == "sin_dato"
    assert apf.classify("up", 0.40, None, None, None) == "sin_dato"
