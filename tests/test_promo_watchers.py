from src.collectors.dexscreener_watcher import DexScreenerWatcher
from src.collectors.pumpfun_recorder import PUMP_PROGRAM
from src.collectors.telegram_watcher import TelegramWatcher, call_rows, extract_addresses, load_channels


class Sink:
    def __init__(self):
        self.rows = []

    async def append(self, venue, table, row):
        self.rows.append((venue, table, row))


class Resp:
    def __init__(self, status, payload):
        self.status, self.payload = status, payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def json(self, content_type=None):
        return self.payload


class Http:
    def __init__(self, by_url):
        self.by_url = by_url

    def get(self, url, timeout=None):
        return Resp(200, self.by_url[url])


SOL = "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr"
EVM = "0x6982508145454Ce325dDbE47a25d4ec3d2311933"


def test_extract_addresses_solana_evm_and_noise():
    text = f"🚀 CA: {SOL} also on base {EVM} and the program {PUMP_PROGRAM} … https://pump.fun/{SOL}"
    got = extract_addresses(text)
    assert ("solana", SOL) in got and ("evm", EVM) in got and ("solana", PUMP_PROGRAM) in got
    assert len(got) == 3                                   # the repeated SOL address counts once
    assert extract_addresses("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa hello 0x123") == []   # not 32-byte base58 / short hex


def test_call_rows_carry_message_and_receive_time():
    rows = call_rows(f"buy {SOL}", 1_000, 2_000, "calls_chan", -100123, 55, 900, True)
    assert rows == [{"ts_message_utc_ns": 1_000, "ts_received_utc_ns": 2_000, "channel": "calls_chan",
                     "channel_id": -100123, "message_id": 55, "chain": "solana", "token_address": SOL,
                     "views": 900, "is_forward": True, "text": f"buy {SOL}"}]


def test_load_channels_normalises(tmp_path):
    p = tmp_path / "c.txt"
    p.write_text("@alpha\nhttps://t.me/beta/\n# comment\n-100123  # private\n\n", encoding="utf-8")
    assert load_channels(p) == ["alpha", "beta", -100123]


def test_telegram_watcher_off_without_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    ok, why = TelegramWatcher(Sink(), tmp_path).ready()
    assert not ok and "TELEGRAM_API_ID" in why


async def test_dexscreener_records_new_boosts_and_profiles_once():
    from src.collectors import dexscreener_watcher as d
    boosts = [{"chainId": "solana", "tokenAddress": SOL, "amount": 10, "totalAmount": 10, "url": "u", "links": []}]
    profiles = {"chainId": "bsc", "tokenAddress": EVM, "description": "x"}       # a single object is accepted too
    sink = Sink()
    w = DexScreenerWatcher(sink, http=Http({d.BOOSTS_URL: boosts, d.PROFILES_URL: profiles}))
    assert await w.poll_once() == 2
    assert await w.poll_once() == 0                         # nothing new
    boosts.append({"chainId": "solana", "tokenAddress": SOL, "amount": 20, "totalAmount": 30})
    assert await w.poll_once() == 1                         # same token, boost total went up -> new row
    tables = [t for _, t, _ in sink.rows]
    assert tables == ["token_boosts", "token_profiles", "token_boosts"]
    assert sink.rows[2][2]["total_amount"] == 30 and sink.rows[1][2]["chain_id"] == "bsc"


def test_read_secret_handles_powershell_utf16_and_bom(tmp_path, monkeypatch):
    from src.collectors.telegram_watcher import read_secret
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    (tmp_path / ".env").write_text("OTHER=1\nTELEGRAM_API_ID = 12345\n", encoding="utf-16")
    assert read_secret("TELEGRAM_API_ID", tmp_path) == "12345"
    (tmp_path / ".env").write_text("TELEGRAM_API_ID=777\n", encoding="utf-8-sig")
    assert read_secret("TELEGRAM_API_ID", tmp_path) == "777"


def test_discover_score_counts_contract_posts_per_day():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("td", Path(__file__).resolve().parents[1] / "scripts" / "telegram_discover.py")
    td = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(td)
    now = 1_000_000.0
    msgs = [(now - 3600 * h, f"CA {SOL}" if h % 2 == 0 else "gm") for h in range(48)]   # 2 days, CA every 2 h
    s = td.score(msgs, now)
    assert s["ca_posts"] == 24 and abs(s["ca_per_day"] - 24 / (47 / 24)) < 1e-9 and s["solana_share"] == 1.0
    assert s["last_post_h"] == 0 and td.keep(s, 3, 24)
    assert not td.keep(td.score([(now - 90_000, f"CA {SOL}")], now), 0.1, 24)        # idle > 24 h
    assert td.score([], now)["ca_per_day"] == 0
