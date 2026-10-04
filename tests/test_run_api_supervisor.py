import importlib.util
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location("run_api", Path(__file__).resolve().parents[1] / "scripts" / "run_api.py")
run_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_api)


def test_detects_code_change_and_ignores_pycache(tmp_path):
    (tmp_path / "src").mkdir()
    f = tmp_path / "src" / "a.py"
    f.write_text("x = 1")
    (tmp_path / "src" / "__pycache__").mkdir()
    s1 = run_api.snapshot(tmp_path, ["src"])
    (tmp_path / "src" / "__pycache__" / "a.cpython-311.pyc").write_text("junk")
    assert not run_api.changed(s1, run_api.snapshot(tmp_path, ["src"]))
    time.sleep(0.01)
    f.write_text("x = 2")
    import os
    os.utime(f, (time.time() + 5, time.time() + 5))
    assert run_api.changed(s1, run_api.snapshot(tmp_path, ["src"]))


def test_new_file_counts_as_change(tmp_path):
    (tmp_path / "src").mkdir()
    s1 = run_api.snapshot(tmp_path, ["src"])
    (tmp_path / "src" / "b.py").write_text("y = 1")
    assert run_api.changed(s1, run_api.snapshot(tmp_path, ["src"]))
