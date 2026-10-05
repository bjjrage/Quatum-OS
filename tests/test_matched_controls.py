from src.research.matched_controls import (
    MATCHED_CONTROL_V2,
    UNMATCHED_CONTROL_V1,
    match_control_v2,
)

AS_OF = 1_800_000_000_000


def feature(qv=100.0, ret=0.02, vol=0.04, ts=AS_OF):
    return {"qv30": qv, "ret3": ret, "vol30": vol, "as_of_ms": ts}


def test_matched_v2_uses_causal_nearest_controls_without_reuse():
    targets = {"T1": feature(), "T2": feature(qv=120)}
    candidates = {"T1": feature(), "A": feature(qv=110), "B": feature(qv=125),
                  "FUTURE": feature(ts=AS_OF + 1)}
    result = match_control_v2(targets, candidates, AS_OF, seed=9)
    assert result["T1"]["control_symbol"] == "A"
    assert result["T2"]["control_symbol"] == "B"
    assert result["T1"]["status"] == "MATCHED"
    assert result["T1"]["match_version"] == MATCHED_CONTROL_V2
    assert result["T1"]["control_as_of_ms"] <= AS_OF
    assert len({r["control_symbol"] for r in result.values()}) == 2
    assert "FUTURE" not in {r["control_symbol"] for r in result.values()}


def test_no_match_for_poor_or_missing_features_and_deterministic_seed():
    targets = {"T": feature()}
    candidates = {"TOO_ILLIQUID": feature(qv=201), "TOO_DIFFERENT": feature(ret=0.071),
                  "MISSING": {"qv30": 100, "ret3": 0.02, "as_of_ms": AS_OF}}
    no_match = match_control_v2(targets, candidates, AS_OF)
    assert no_match["T"]["status"] == "NO_MATCH"
    assert no_match["T"]["control_symbol"] is None
    ties = {"Z": feature(), "A": feature()}
    assert match_control_v2(targets, ties, AS_OF, seed=44) == match_control_v2(targets, ties, AS_OF, seed=44)


def test_v1_control_is_preserved_as_a_distinct_version():
    assert UNMATCHED_CONTROL_V1 == "UNMATCHED_CONTROL_V1"
    assert MATCHED_CONTROL_V2 != UNMATCHED_CONTROL_V1
