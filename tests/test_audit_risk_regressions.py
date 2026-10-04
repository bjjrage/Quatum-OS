"""Pre-paper audit regressions for the deterministic Risk Engine."""
from src.risk.engine import DeterministicRiskEngine, ProposedOrder, RiskViolationCode


def _o(oid, side, qty, px=80_000.0):
    return ProposedOrder(oid, "S", "BTC", side, qty, px)


def test_drawdown_breaker_counts_in_flight_orders_for_risk_reducing():
    e = DeterministicRiskEngine(100_000.0)
    e.update_portfolio_state(80_000.0, {"BTC": 1.0}, {"BTC": 80_000.0})  # 20% drawdown, 1 BTC long
    decisions = []
    for i in range(5):
        o = _o(f"z{i}", "SELL", 1.0)
        d = e.evaluate_order(o, current_time_s=10 + i)
        decisions.append(d)
        if d.approved:
            e.register_in_flight(o)
    assert decisions[0].approved, "the first sell genuinely reduces the long"
    assert all(not d.approved for d in decisions[1:])
    assert all(d.violation_code == RiskViolationCode.MAX_DRAWDOWN_EXCEEDED for d in decisions[1:])


def test_sell_that_flips_through_zero_is_not_risk_reducing_under_breaker():
    e = DeterministicRiskEngine(100_000.0)
    e.update_portfolio_state(80_000.0, {"BTC": 1.0}, {"BTC": 80_000.0})
    d = e.evaluate_order(_o("flip", "SELL", 2.0), current_time_s=1)
    assert not d.approved


def test_hold_nan_and_inf_rejected():
    e = DeterministicRiskEngine(100_000.0)
    assert not e.evaluate_order(_o("a", "HOLD", 1.0)).approved
    assert not e.evaluate_order(_o("b", "BUY", float("nan"))).approved
    assert not e.evaluate_order(_o("c", "BUY", 1.0, float("inf"))).approved
