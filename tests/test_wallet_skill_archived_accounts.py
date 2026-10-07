"""Archived strategy registry and reporting separation checks."""

import json

from src.paper.pump_wallet_skill_v1 import ACTIVE_ACCOUNTS, ARCHIVED_ACCOUNTS, WalletSkillPaper


def test_six_archived_accounts_are_not_instantiated_as_active(tmp_path):
    expected = {"grupo", "grupo_nicho", "nicho", "grupo_aguantar", "detector_tarde", "azar"}
    assert set(ARCHIVED_ACCOUNTS) == expected
    assert expected.isdisjoint(ACTIVE_ACCOUNTS)

    paper = WalletSkillPaper(root=tmp_path)
    assert set(paper.accounts) == set(ACTIVE_ACCOUNTS)
    assert all(not (tmp_path / f"pump_{name}" / "state.json").exists() for name in expected)


def test_status_keeps_discovery_and_forward_metrics_separate(tmp_path):
    paper = WalletSkillPaper(root=tmp_path)
    paper.save(1_000.0)
    status_path = tmp_path / "pump_wallet_skill_v1" / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))

    assert "discovery" in status and "forward" in status, (
        "Wallet-skill status has no separately reported discovery and forward cohorts."
    )
    assert "freeze_boundary_uncertain" in status or "freeze_timestamp" in status
