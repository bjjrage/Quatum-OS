"""v1.5 persistence integrity tests (offline; Supabase transport mocked)."""
import json
import re
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.persistence import schema
from src.persistence.backend import (
    LocalPersistenceBackend, ImmutableConflictError, BackendUnavailableError, NotConfiguredError,
)
from src.persistence.catalog import MarketDataCatalog
from src.persistence.config import SupabaseConfig
from src.persistence.domain import (
    AuditLog, CapitalPocketStore, CapitalError, ConfigSnapshotStore, PaperStore, PropProfileStore,
    PropProfileError, RiskStore, HoldoutReplicaError, replicate_holdout_audits,
    make_persisted_experiment_registry, OWN_CAPITAL_BASELINE_USD, AUTHORIZED_LIVE_CAPITAL_USD,
)
from src.persistence.supabase_backend import SupabasePersistenceBackend
from src.persistence.sync import OutboxSyncer

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def be(tmp_path):
    b = LocalPersistenceBackend(tmp_path / "cp.db")
    yield b
    b.close()


class FakeRest:
    """In-memory PostgREST double. `down` simulates an outage."""
    def __init__(self):
        self.rows = {}
        self.down = False
        self.calls = 0

    def request(self, method, path, **kw):  # pragma: no cover - shape adapter not used
        raise NotImplementedError


class FakeRemote(LocalPersistenceBackend):
    """Remote backend double built on the same semantic contract as Supabase backend."""
    def __init__(self, path):
        super().__init__(path)
        self.down = False

    def put(self, table, key, data):
        if self.down:
            raise BackendUnavailableError("outage")
        return super().put(table, key, data)


# ------------------------------------------------------------ schema / config
def test_committed_migration_matches_generator():
    sql = (ROOT / "migrations" / schema.MIGRATION_0001_NAME).read_text(encoding="utf-8")
    assert sql.replace("\r\n", "\n") == schema.render_migration_sql().replace("\r\n", "\n")


def test_committed_migration_0002_matches_generator():
    sql = (ROOT / "migrations" / schema.MIGRATION_0002_NAME).read_text(encoding="utf-8")
    assert sql.replace("\r\n", "\n") == schema.render_migration_0002_sql().replace("\r\n", "\n")


def test_migration_enables_rls_and_revokes_public():
    sql = schema.render_migration_sql()
    assert sql.count("enable row level security") >= len(schema.TABLE_SPECS)
    assert "revoke all" in sql
    assert not re.search(r"create policy[^;]*(anon|authenticated|public)", sql, re.I)


def test_supabase_not_configured_is_explicit():
    cfg = SupabaseConfig.from_env({})
    assert not cfg.is_configured
    assert cfg.status()["status"] == "NOT_CONFIGURED"
    assert "SUPABASE_URL" in cfg.missing()


def test_config_repr_never_leaks_secret():
    cfg = SupabaseConfig.from_env({"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "SECRETVALUE123"})
    assert "SECRETVALUE123" not in repr(cfg)
    assert "SECRETVALUE123" not in json.dumps(cfg.status())


def test_no_secrets_committed():
    pat = re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}")
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    for f in out:
        if f.endswith((".py", ".md", ".sql", ".example", ".yml", ".yaml", ".json", ".toml")):
            p = ROOT / f
            if p.exists():
                assert not pat.search(p.read_text(encoding="utf-8", errors="ignore")), f
    assert (ROOT / ".env.example").exists()
    ex = (ROOT / ".env.example").read_text()
    for line in ex.splitlines():
        if "=" in line and not line.startswith("#"):
            assert line.split("=", 1)[1].strip() == ""


# --------------------------------------------------------------- local backend
def test_local_round_trip_and_restart(tmp_path):
    p = tmp_path / "a.db"
    b = LocalPersistenceBackend(p)
    b.put("experiments", "e1", {"experiment_id": "e1", "strategy_id": "S", "gate_result": "FAIL"})
    b.close()
    b2 = LocalPersistenceBackend(p)
    assert b2.get("experiments", "e1")["strategy_id"] == "S"
    b2.close()


def test_immutable_conflict(be):
    be.put("risk_decisions", "d1", {"decision_id": "d1", "approved": True})
    assert be.put("risk_decisions", "d1", {"decision_id": "d1", "approved": True}) == "UNCHANGED"
    with pytest.raises(ImmutableConflictError):
        be.put("risk_decisions", "d1", {"decision_id": "d1", "approved": False})


def test_outbox_retry_and_idempotent_duplicate_sync(tmp_path, be):
    remote = FakeRemote(tmp_path / "remote.db")
    be.put("experiments", "e1", {"experiment_id": "e1", "strategy_id": "S"})
    remote.down = True
    rep = OutboxSyncer(be, remote, base_delay=0.0).sync_once()
    assert be.outbox_stats().get("PENDING", 0) >= 1
    assert be.get("experiments", "e1") is not None  # local capture unaffected by outage
    remote.down = False
    OutboxSyncer(be, remote, base_delay=0.0).sync_once()
    OutboxSyncer(be, remote, base_delay=0.0).sync_once()  # duplicate sync
    assert remote.count("experiments") == 1
    assert be.outbox_stats().get("SYNCED", 0) >= 1


def test_sync_not_configured_leaves_pending(be):
    remote = SupabasePersistenceBackend(SupabaseConfig.from_env({}))
    be.put("experiments", "e1", {"experiment_id": "e1", "strategy_id": "S"})
    OutboxSyncer(be, remote).sync_once()
    stats = be.outbox_stats()
    assert stats.get("PENDING", 0) == 1 and stats.get("FAILED", 0) == 0


class _Transport:
    def __init__(self, status=200, body=None):
        self.status, self.body, self.calls = status, body if body is not None else [], []

    def request(self, method, path, **kw):
        self.calls.append((method, path))
        if self.status >= 500:
            raise BackendUnavailableError("5xx")
        return self.body


def test_supabase_backend_mocked_transport_unavailable():
    cfg = SupabaseConfig.from_env({"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "k"})
    b = SupabasePersistenceBackend(cfg, transport=_Transport(status=503))
    with pytest.raises(BackendUnavailableError):
        b.put("experiments", "e1", {"experiment_id": "e1", "strategy_id": "S"})


# ------------------------------------------------------------- parquet catalog
def _write_part(root: Path, name="part-1-aaaaaaaa.parquet", ts=1_000):
    d = root / "binance" / "table=trades" / "year=2026" / "month=10" / "day=03" / "hour=01"
    d.mkdir(parents=True, exist_ok=True)
    f = d / name
    pq.write_table(pa.table({"ts_exchange_ns": [ts, ts + 5], "x": [1, 2]}), f)
    return f


def test_catalog_registers_and_detects_tamper(tmp_path, be):
    raw = tmp_path / "raw"
    f = _write_part(raw)
    cat = MarketDataCatalog(be, raw_root=raw)
    assert cat.scan("run1", "cfp") == 1
    rows = be.list("market_data_files")
    assert rows[0]["row_count"] == 2 and rows[0]["upload_status"] == "UPLOAD_PENDING"
    assert cat.scan("run1", "cfp") == 0  # idempotent
    f.write_bytes(f.read_bytes() + b"x")
    fid = be.list("market_data_files")[0]["file_id"]
    assert cat.verify_local(fid) is False
    rec = be.list("market_data_files")[0]
    assert rec["upload_status"] == "INTEGRITY_FAILED"
    assert rec["sha256"] != rec.get("observed_sha256")


def test_catalog_skips_tmp(tmp_path, be):
    raw = tmp_path / "raw"
    t = raw / ".tmp"
    t.mkdir(parents=True)
    (t / "x.parquet.tmp").write_bytes(b"junk")
    assert MarketDataCatalog(be, raw_root=raw).scan("r", "c") == 0


def test_replicator_upload_failure_keeps_local_and_not_configured(tmp_path, be):
    from src.persistence.replication import ParquetReplicator
    raw = tmp_path / "raw"
    f = _write_part(raw)
    cat = MarketDataCatalog(be, raw_root=raw)
    cat.scan("r", "c")
    ParquetReplicator(cat, None, None).replicate_once()
    assert f.exists()
    assert be.list("market_data_files")[0]["upload_status"] == "UPLOAD_PENDING"

    class Boom:
        def upload(self, *a, **k):
            raise BackendUnavailableError("down")

        def head(self, *a, **k):
            return None

    ParquetReplicator(cat, Boom(), "bkt").replicate_once()
    assert f.exists()
    assert be.list("market_data_files")[0]["upload_status"] == "UPLOAD_FAILED"


# ------------------------------------------------------------------ experiments
def _record(i, strategy="STR-X", gate="FAIL"):
    from src.research.experiments import ExperimentRecord
    fields = ExperimentRecord.model_fields
    base = dict(
        experiment_id=f"exp-{i}", strategy_id=strategy, strategy_version="1", git_sha="abc",
        dataset_fingerprint="d", config_fingerprint="c", feature_definition_hash="f", parameters={},
        entry_model="e", exit_model="x", factor_model="m", regime_definition="r", universe_definition="u",
        cost_model_version="1", research_period="a", validation_period="b", holdout_period="c",
        random_seed=1, result_metrics={}, gate_result=gate, created_at="2026-01-01T00:00:00Z",
        falsification_evidence="", reasons=[],
    )
    return ExperimentRecord(**{k: v for k, v in base.items() if k in fields})


def test_failed_experiment_persists_and_trial_count_survives_restart(tmp_path):
    db, d = tmp_path / "cp.db", tmp_path / "exp"
    b = LocalPersistenceBackend(db)
    reg = make_persisted_experiment_registry(d, b)
    for i in range(3):
        reg.record_experiment(_record(i))
    assert reg.get_trial_count("STR-X") == 3
    assert all(r["gate_result"] == "FAIL" for r in b.list("experiments"))
    b.close()
    b2 = LocalPersistenceBackend(db)
    reg2 = make_persisted_experiment_registry(d, b2)
    assert reg2.get_trial_count("STR-X") == 3
    # Local JSON lost but replica remains -> count never undercounts
    for f in d.glob("*.json"):
        f.unlink()
    reg3 = make_persisted_experiment_registry(d, b2)
    assert reg3.get_trial_count("STR-X") == 3
    b2.close()


# --------------------------------------------------------------------- holdouts
def test_holdout_replica_corrupt_fail_closed(tmp_path, be):
    p = tmp_path / "audits.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(HoldoutReplicaError):
        replicate_holdout_audits(p, be)
    assert be.count("holdout_access_audit") == 0


def test_holdout_audit_survives_restart(tmp_path):
    p = tmp_path / "audits.json"
    p.write_text(json.dumps([{"audit_id": "h1", "strategy_id": "S", "strategy_version": "1",
                              "timestamp_utc": "2026-01-01T00:00:00+00:00"}]), encoding="utf-8")
    b = LocalPersistenceBackend(tmp_path / "cp.db")
    assert replicate_holdout_audits(p, b) == 1
    assert replicate_holdout_audits(p, b) == 1  # idempotent
    b.close()
    b2 = LocalPersistenceBackend(tmp_path / "cp.db")
    assert b2.get("holdout_access_audit", "h1") is not None
    b2.close()


# ------------------------------------------------------------------ paper / risk
def test_paper_orders_fills_survive_restart_and_idempotent(tmp_path):
    p = tmp_path / "cp.db"
    b = LocalPersistenceBackend(p)
    s = PaperStore(b)
    s.record_order({"order_id": "o1", "paper_account_id": "A", "strategy_id": "S", "symbol": "BTC", "status": "NEW"}, "k1")
    s.record_order({"order_id": "o1", "paper_account_id": "A", "strategy_id": "S", "symbol": "BTC", "status": "FILLED"}, "k1")
    s.record_fill({"fill_id": "f1", "order_id": "o1", "paper_account_id": "A", "symbol": "BTC", "qty": 1})
    b.close()
    b2 = LocalPersistenceBackend(p)
    s2 = PaperStore(b2)
    assert len(s2.orders()) == 1 and s2.orders()[0]["status"] == "FILLED"
    assert len(s2.fills()) == 1
    with pytest.raises(ValueError):
        s2.record_order({"order_id": "o2"}, "")
    b2.close()


def test_risk_veto_and_kill_switch_survive_restart(tmp_path):
    from src.risk.engine import DeterministicRiskEngine
    p = tmp_path / "cp.db"
    b = LocalPersistenceBackend(p)
    rs = RiskStore(b)
    assert rs.kill_switch_state() == "UNKNOWN"  # UNKNOWN != SAFE
    rs.record_decision({"approved": False, "violation_code": "KILL_SWITCH_ACTIVE"}, "S", "BTC", decision_id="d1")
    rs.record_kill_switch("ACTIVATE", "ops", "test")
    with pytest.raises(ValueError):
        rs.record_kill_switch("RESET", "", "")
    b.close()
    b2 = LocalPersistenceBackend(p)
    rs2 = RiskStore(b2)
    assert rs2.decisions()[0]["approved"] is False
    assert rs2.kill_switch_state() == "ACTIVE"
    b2.close()


# ---------------------------------------------------------- capital / prop / etc.
def test_capital_baseline_and_live_locked(be):
    st = CapitalPocketStore(be)
    st.seed_baseline()
    own = st.get("OWN_MAIN")
    assert own["amount_usd"] == OWN_CAPITAL_BASELINE_USD == 2000.0
    assert own["state_kind"] == "HYPOTHETICAL"
    assert own["authorized_live_capital_usd"] == AUTHORIZED_LIVE_CAPITAL_USD == 0.0
    with pytest.raises(CapitalError):
        st.upsert("OWN_MAIN", "OWN", "REAL", 2000.0, authorized_live_capital_usd=100.0)
    with pytest.raises(CapitalError):
        st.upsert("X", "OWN", "BOGUS", 1.0)


def test_prop_verified_requires_evidence_and_fiction_blocked(be):
    st = PropProfileStore(be)
    with pytest.raises(PropProfileError):
        st.put_profile("RealFirm", "v1", "VERIFIED", rules={"dd": 5})
    with pytest.raises(PropProfileError):
        st.put_profile("AlphaFunding", "v1", "VERIFIED", rules={"dd": 5}, evidence_refs=["x"],
                       verified_at="2026-01-01", verified_by="me")
    st.put_profile("RealFirm", "v1")  # UNKNOWN stays UNKNOWN
    assert st.get("RealFirm", "v1")["verification_status"] == "UNKNOWN"
    st.put_profile("RealFirm", "v2", "VERIFIED", rules={"dd": 5}, evidence_refs=["doc://rules"],
                   verified_at="2026-01-01T00:00:00Z", verified_by="analyst")
    assert st.get("RealFirm", "v2")["verification_status"] == "VERIFIED"
    assert be.count("prop_profile_evidence") == 1


def test_fixture_profiles_only_when_explicit(be):
    with pytest.raises(PropProfileError):
        PropProfileStore(be).put_profile("AlphaFunding", "v1", "PENDING", is_fixture=True)
    fx = PropProfileStore(be, allow_fixture_providers=True)
    fx.put_profile("AlphaFunding", "v1", "PENDING", is_fixture=True)
    assert fx.get("AlphaFunding", "v1")["data_source"] == "FIXTURE"


def test_audit_chain_detects_tamper(be):
    a = AuditLog(be, git_sha="abc", config_fingerprint="cfp")
    for i in range(3):
        a.append("TEST", "me", "thing", str(i), {"i": i})
    assert a.verify_chain()["status"] == "OK"
    # Tamper directly in sqlite (bypassing the API): alter the middle event's payload
    import sqlite3
    be.close()
    con = sqlite3.connect(be.db_path)
    rows = con.execute("select key, data from records where table_name='audit_events'").fetchall()
    key, data = sorted(rows, key=lambda r: json.loads(r[1])["seq"])[1]
    d = json.loads(data)
    d["payload"] = {"i": 999}
    con.execute("update records set data=? where table_name='audit_events' and key=?", (json.dumps(d), key))
    con.commit()
    con.close()
    be2 = LocalPersistenceBackend(be.db_path)
    assert AuditLog(be2).verify_chain()["status"] == "BROKEN"
    be2.close()


def test_config_snapshots_versioned_and_fingerprinted(be):
    st = ConfigSnapshotStore(be)
    a = st.snapshot("RISK", {"max_dd": 1})
    b = st.snapshot("RISK", {"max_dd": 1})
    c = st.snapshot("RISK", {"max_dd": 2})
    assert a["snapshot_id"] == b["snapshot_id"] != c["snapshot_id"]
    with pytest.raises(ValueError):
        st.snapshot("NOPE", {})


# ------------------------------------------------------------------- API status
def test_api_persistence_status_is_honest():
    from fastapi.testclient import TestClient
    from apps.api.main import app
    r = TestClient(app).get("/api/system/persistence")
    assert r.status_code == 200
    j = r.json()
    assert j["remote"]["status"] == "NOT_CONFIGURED"
    assert j["live_authorized_capital_usd"] == 0.0
    assert j["own_capital_baseline_usd"] == 2000.0
