"""Tests for real venue adapter plumbing (Binance USD-M, Bybit v5, Deribit).

Uses a recording mock Transport to verify:
- HMAC-SHA256 signing (Binance & Bybit)
- Bearer token authentication (Deribit)
- Strict SANDBOX vs LIVE URL separation (no crossover)
- SubmitPermit required for mutations (fail-closed)
- Error classification (RateLimited, AuthFailure, UnknownOutcomeError, VenueUnavailable)
- Secret redaction in exceptions and headers
"""
import pytest
from src.execution_plane.adapters.base import (
    AuthFailure,
    LiveLockedError,
    SubmitPermit,
    TransportNotConfigured,
    UnknownOutcomeError,
    VenueUnavailable,
)
from tests.helpers.auth import issue_permit
from src.execution_plane.adapters.real import (
    BinanceUSDMAdapter,
    BybitAdapter,
    DeribitAdapter,
    HttpResponse,
    TransportConnectError,
    TransportTimeout,
)
from src.execution_plane.models import ExecutionMode, InstrumentMeta, OrderIntent
from src.execution_plane.security import CredentialProvider
from src.execution_plane.telemetry import RateLimited


class MockTransport:
    def __init__(self, handler=None):
        self.calls = []
        self.handler = handler or (lambda method, url, headers, params, body: HttpResponse(200, {}))

    def request(self, method, url, headers=None, params=None, json_body=None, timeout_s=10.0):
        self.calls.append({
            "method": method,
            "url": url,
            "headers": dict(headers or {}),
            "params": dict(params or {}),
            "body": json_body,
        })
        return self.handler(method, url, headers, params, json_body)


@pytest.fixture
def meta_btc():
    return InstrumentMeta(
        symbol="BTCUSDT",
        venue="binance_perp",
        venue_symbol="BTCUSDT",
        tick_size=0.1,
        step_size=0.001,
        min_qty=0.001,
        min_notional=5.0,
        base_asset="BTC",
        quote_asset="USDT",
        margin_asset="USDT",
    )


@pytest.fixture
def sample_intent():
    return OrderIntent(
        intent_id="intent_1",
        strategy_id="STR-001",
        strategy_version="1.0.0",
        capital_pocket_id="pocket-1",
        venue="binance_perp",
        symbol="BTCUSDT",
        side="BUY",
        order_type="LIMIT",
        quantity=0.01,
        limit_price=60000.0,
        market_data_timestamp_ns=1_700_000_000_000_000_000,
        decision_timestamp_ns=1_700_000_000_000_000_000,
        max_signal_age_ms=1000.0,
        created_at_ns=1_700_000_000_000_000_000,
    )


def test_transport_not_configured_by_default():
    ad = BinanceUSDMAdapter(environment="LIVE")
    assert ad.transport is None
    with pytest.raises(TransportNotConfigured):
        ad.get_server_time()


def test_binance_sandbox_vs_live_urls():
    live = BinanceUSDMAdapter(environment="LIVE")
    sbx = BinanceUSDMAdapter(environment="SANDBOX")
    assert "fapi.binance.com" in live.base_url
    assert "testnet.binancefuture.com" in sbx.base_url
    assert live.base_url != sbx.base_url


def test_bybit_sandbox_vs_live_urls():
    live = BybitAdapter(environment="LIVE")
    sbx = BybitAdapter(environment="SANDBOX")
    assert "api.bybit.com" in live.base_url
    assert "api-testnet.bybit.com" in sbx.base_url
    assert live.base_url != sbx.base_url


def test_deribit_testnet_vs_live_urls():
    live = DeribitAdapter(environment="LIVE")
    sbx = DeribitAdapter(environment="SANDBOX")
    assert "www.deribit.com" in live.base_url
    assert "test.deribit.com" in sbx.base_url
    assert live.base_url != sbx.base_url


def test_binance_hmac_signing():
    cp = CredentialProvider({
        "BINANCE_API_KEY": "test_api_key",
        "BINANCE_API_SECRET": "test_api_secret",
    })
    mt = MockTransport(lambda m, u, h, p, b: HttpResponse(200, {"serverTime": 1700000000000}))
    ad = BinanceUSDMAdapter(credentials=cp, environment="LIVE", transport=mt)
    
    # Server time is public (not signed)
    t = ad.get_server_time()
    assert t == 1700000000000
    assert "signature" not in mt.calls[0]["params"]

    # Account balances is private (signed)
    def handler(m, u, h, p, b):
        if "serverTime" in u:
            return HttpResponse(200, {"serverTime": 1700000000000})
        if "positionRisk" in u or "openOrders" in u:
            return HttpResponse(200, [])
        return HttpResponse(200, {
            "totalMarginBalance": "1000.0",
            "availableBalance": "500.0",
            "totalInitialMargin": "0.0",
        })
    mt.handler = handler
    ad.get_balances()
    last = [c for c in mt.calls if "account" in c["url"]][0]
    assert "signature" in last["params"]
    assert last["headers"].get("X-MBX-APIKEY") == "test_api_key"
    assert "test_api_secret" not in repr(last)


def test_bybit_v5_signing():
    cp = CredentialProvider({
        "BYBIT_API_KEY": "bybit_key_123",
        "BYBIT_API_SECRET": "bybit_secret_456",
    })
    mt = MockTransport(lambda m, u, h, p, b: HttpResponse(200, {"retCode": 0, "result": {"timeSecond": "1700000000"}}))
    ad = BybitAdapter(credentials=cp, environment="LIVE", transport=mt)
    
    ad.get_server_time()
    assert mt.calls[0]["url"].endswith("/v5/market/time")

    # Account info is signed via headers
    mt.handler = lambda m, u, h, p, b: HttpResponse(200, {"retCode": 0, "result": {"list": [{"coin": [{"coin": "USDT", "walletBalance": "2000.0", "availableToWithdraw": "1500.0"}]}]}})
    ad.get_balances()
    headers = mt.calls[-1]["headers"]
    assert "X-BAPI-API-KEY" in headers
    assert "X-BAPI-SIGN" in headers
    assert "X-BAPI-TIMESTAMP" in headers
    assert "bybit_secret_456" not in repr(headers)


def test_deribit_auth_token():
    cp = CredentialProvider({
        "DERIBIT_CLIENT_ID": "deribit_id_1",
        "DERIBIT_CLIENT_SECRET": "deribit_secret_2",
    })
    def handler(m, u, h, p, b):
        if "public/auth" in u:
            return HttpResponse(200, {"result": {"access_token": "token_abc_123", "expires_in": 999}})
        if "private/get_account_summary" in u:
            return HttpResponse(200, {"result": {"equity": 2000.0, "available_funds": 1800.0, "currency": "USDT"}})
        return HttpResponse(200, {"result": {}})

    mt = MockTransport(handler)
    ad = DeribitAdapter(credentials=cp, environment="LIVE", transport=mt)
    ad.get_account()
    
    assert any("public/auth" in c["url"] for c in mt.calls)
    priv_call = [c for c in mt.calls if "private/get_account_summary" in c["url"]][0]
    assert priv_call["headers"]["Authorization"] == "Bearer token_abc_123"


def test_submit_permit_enforcement(sample_intent, meta_btc):
    cp = CredentialProvider({
        "BINANCE_API_KEY": "key",
        "BINANCE_API_SECRET": "secret",
    })
    mt = MockTransport()
    ad = BinanceUSDMAdapter(credentials=cp, environment="LIVE", transport=mt)
    
    # 1. Calling submit_order with invalid permit raises
    fake_permit = "not_a_real_permit"
    with pytest.raises(Exception):
        ad.submit_order(fake_permit, sample_intent, meta_btc)

    # 2. Permit with LIVE mode but $0 authorized capital raises LiveLockedError
    locked_permit = issue_permit(
        kind="SUBMIT",
        venue="binance_perp",
        client_order_id=sample_intent.client_order_id,
        mode=ExecutionMode.LIVE,
        authorized_live_capital_usd=0.0,
        risk_approved=True,
        issued_ns=1_700_000_000_000_000_000,
    )
    with pytest.raises(LiveLockedError):
        ad.submit_order(locked_permit, sample_intent, meta_btc)


def test_http_error_mappings():
    cp = CredentialProvider({
        "BINANCE_API_KEY": "k",
        "BINANCE_API_SECRET": "s",
        "BINANCE_TESTNET_API_KEY": "tk",
        "BINANCE_TESTNET_API_SECRET": "ts",
    })
    
    # Rate limit 429
    mt_429 = MockTransport(lambda m, u, h, p, b: HttpResponse(429, {"msg": "Too many requests"}, {"Retry-After": "2"}))
    ad = BinanceUSDMAdapter(credentials=cp, environment="LIVE", transport=mt_429)
    with pytest.raises(RateLimited) as exc:
        ad.get_server_time()
    assert exc.value.retry_after_s == 2.0

    # Auth failure 401
    mt_401 = MockTransport(lambda m, u, h, p, b: HttpResponse(401, {"msg": "Invalid API-key"}))
    ad = BinanceUSDMAdapter(credentials=cp, environment="LIVE", transport=mt_401)
    with pytest.raises(AuthFailure):
        ad.get_server_time()

    # 500 on mutation -> UnknownOutcomeError
    mt_500 = MockTransport(lambda m, u, h, p, b: HttpResponse(500, {"msg": "Internal error"}))
    ad = BinanceUSDMAdapter(credentials=cp, environment="SANDBOX", transport=mt_500)
    permit = issue_permit(
        kind="CANCEL",
        venue="binance_perp",
        client_order_id="cid1",
        mode=ExecutionMode.SANDBOX,
        authorized_live_capital_usd=100.0,
        risk_approved=True,
        issued_ns=1_700_000_000_000_000_000,
    )
    with pytest.raises(UnknownOutcomeError):
        ad.cancel_order(permit, "cid1", "BTCUSDT")

    # Connect error before send -> VenueUnavailable(pre_send=True)
    def raise_connect(m, u, h, p, b):
        raise TransportConnectError("connection refused")
    mt_conn = MockTransport(raise_connect)
    ad = BinanceUSDMAdapter(credentials=cp, environment="LIVE", transport=mt_conn)
    with pytest.raises(VenueUnavailable) as exc:
        ad.get_server_time()
    assert exc.value.pre_send is True

    # Timeout after send -> UnknownOutcomeError on mutation
    def raise_timeout(m, u, h, p, b):
        raise TransportTimeout(sent=True, message="read timeout")
    mt_to = MockTransport(raise_timeout)
    ad = BinanceUSDMAdapter(credentials=cp, environment="SANDBOX", transport=mt_to)
    with pytest.raises(UnknownOutcomeError):
        ad.cancel_order(permit, "cid1", "BTCUSDT")
