"""Global test isolation.

Every test gets its own control-plane SQLite DB and fresh service singletons, so kill-switch
activations, audit events and governance state can neither leak between tests nor be written
into the real `data/control_plane/control_plane.db`.
"""
import pytest


@pytest.fixture(autouse=True)
def _isolated_control_plane(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_OS_CONTROL_PLANE_DB", str(tmp_path / "control_plane.db"))
    from apps.api.services.data_service import QuantOSDataService
    from src.execution_plane.service import ExecutionPlaneService

    QuantOSDataService._instance = None
    ExecutionPlaneService.reset_instance()
    yield
    QuantOSDataService._instance = None
    ExecutionPlaneService.reset_instance()
