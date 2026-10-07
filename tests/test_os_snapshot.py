import json
import subprocess

import pytest

from scripts import os_snapshot as S


def _fake_root(tmp_path):
    r = tmp_path / "root"
    (r / "data" / "paper" / "flujo_v1").mkdir(parents=True)
    (r / "data" / "paper" / "flujo_v1" / "state.json").write_text(json.dumps(
        {"cash": 10000, "posiciones": {f"S{i}": i for i in range(3)}, "rebalanceos": list(range(40)),
         "text": "never exported"}), encoding="utf-8")
    pu = r / "data" / "paper" / "poly_updown"
    pu.mkdir(parents=True)
    ev = [{"ts": 1, "kind": "signal", "slug": "btc-updown-5m-1"},
          {"ts": 2, "kind": "fill", "slug": "btc-updown-5m-1", "side": "up", "price": 0.4, "usd": 20, "t": 2},
          {"ts": 300, "kind": "settle", "slug": "btc-updown-5m-1", "pnl": 29.0}]
    (pu / "events.jsonl").write_text("\n".join(json.dumps(e) for e in ev), encoding="utf-8")
    logs = r / "data" / "runtime" / "logs"
    logs.mkdir(parents=True)
    (logs / "recorder.log").write_text(
        '{"level": "INFO", "message": "ok"}\n'
        '{"level": "WARNING", "message": "RPC https://mainnet.helius-rpc.com/?api-key=SECRETKEY123 timeout"}\n'
        '{"level": "ERROR", "message": "xai-abcdefghijklmnopqrstuvwxyz failed"}\n', encoding="utf-8")
    t = r / "data" / "raw" / "telegram" / "table=calls" / "year=2026"
    t.mkdir(parents=True)
    (t / "part-1.parquet").write_bytes(b"PAR1xxxxPAR1")
    return r


def test_build_contents_and_redaction(tmp_path):
    r = _fake_root(tmp_path)
    snap = {"generado_utc": "x", "polymarket": S.poly_summary(r), "papers": S.paper_states(r),
            "salud": {}, "recorders": S.recorder_activity(r), "logs": S.log_problems(r)}
    blob = json.dumps(snap)
    assert "SECRETKEY123" not in blob and "abcdefghijklmnop" not in blob and "[CLAVE]" in blob
    assert "never exported" not in blob                                   # free-text fields dropped
    assert snap["polymarket"]["llenadas"] == 1 and snap["polymarket"]["pnl_binance_usd"] == 29.0
    reb = snap["papers"]["flujo_v1"]["estado"]["rebalanceos"]
    assert len(reb) == 13 and reb[0].startswith("... 28")                 # long lists trimmed to the tail
    assert snap["recorders"]["telegram/calls"]["archivos_ultima_hora"] == 1
    assert list(snap["logs"]["recorder.log"])[0].count("WARNING") == 1 and len(snap["logs"]["recorder.log"]) == 2
    assert "Polymarket" in S.to_markdown(snap)


@pytest.mark.skipif(subprocess.run(["git", "--version"], capture_output=True).returncode != 0, reason="no git")
def test_push_creates_snapshots_branch_without_touching_worktree(tmp_path, monkeypatch):
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "mywork", str(work)], check=True)
    (work / "f.txt").write_text("mine", encoding="utf-8")
    for cmd in (["add", "f.txt"], ["-c", "user.name=a", "-c", "user.email=a@b", "commit", "-qm", "w"],
                ["remote", "add", "origin", str(remote)]):
        subprocess.run(["git", *cmd], cwd=work, check=True)
    (work / "f.txt").write_text("uncommitted change", encoding="utf-8")
    monkeypatch.setattr(S, "ROOT", work)
    c1 = S.push({"latest.md": "# one", "latest.json": "{}"})
    c2 = S.push({"latest.md": "# two", "latest.json": "{}"})
    show = lambda *a: subprocess.run(["git", *a], cwd=work, capture_output=True, text=True).stdout.strip()
    assert show("rev-parse", "--abbrev-ref", "HEAD") == "mywork"
    assert (work / "f.txt").read_text(encoding="utf-8") == "uncommitted change"
    remote_head = subprocess.run(["git", "rev-parse", "refs/heads/snapshots"], cwd=remote, capture_output=True,
                                 text=True).stdout.strip()
    assert remote_head == c2 and show("rev-parse", f"{c2}^") == c1         # history kept, one commit per snapshot
    assert show("show", f"{c2}:latest.md") == "# two"
    assert show("ls-tree", "--name-only", c2).split("\n") == ["latest.json", "latest.md"]   # no "\r" in names


def test_git_stdin_is_bytes_so_windows_cannot_add_carriage_returns(monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen.update(kw)

        class R:
            returncode, stdout, stderr = 0, b"abc\n", b""
        return R()

    monkeypatch.setattr(S.subprocess, "run", fake_run)
    assert S.git("mktree", input_text="100644 blob x\tlatest.md\n") == "abc"
    assert isinstance(seen["input"], bytes) and b"\r" not in seen["input"] and not seen.get("text")
