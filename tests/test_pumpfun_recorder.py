import asyncio
import base64
import json
import struct

from src.collectors.pumpfun_recorder import (DISC_COMPLETE, DISC_CREATE, DISC_TRADE, PUMP_PROGRAM, PumpfunRecorder,
                                             b58, decode_event, events_from_logs, resolve_url)

_A = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s: str) -> bytes:
    n = 0
    for c in s:
        n = n * 58 + _A.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\0" * (len(s) - len(s.lstrip("1"))) + raw


def pk(i: int) -> bytes:
    return bytes([i]) * 32


def s(x: str) -> bytes:
    b = x.encode()
    return struct.pack("<I", len(b)) + b


def trade_bytes(full=True):
    b = DISC_TRADE + pk(1) + struct.pack("<QQ", 2_000_000_000, 35_000_000_000_000) + b"\x01" + pk(2)
    b += struct.pack("<q", 1_791_000_000) + struct.pack("<QQQQ", 30_000_000_000, 1_000_000_000_000_000, 1, 2)
    if full:
        b += pk(3) + struct.pack("<QQ", 95, 19_000_000) + pk(4) + struct.pack("<QQ", 5, 1_000_000) + b"\x00" * 40
    return b


def test_base58_roundtrip_program_id():
    assert b58(b58decode(PUMP_PROGRAM)) == PUMP_PROGRAM
    assert b58(b"\0" * 32) == "1" * 32


def test_decode_trade_full_and_old_format():
    kind, ev = decode_event(trade_bytes())
    assert kind == "trade" and ev["is_buy"] and ev["sol_amount"] == 2_000_000_000
    assert ev["mint"] == b58(pk(1)) and ev["user"] == b58(pk(2)) and ev["creator"] == b58(pk(4))
    assert ev["fee"] == 19_000_000 and ev["creator_fee"] == 1_000_000 and ev["ts_chain_s"] == 1_791_000_000
    kind, ev = decode_event(trade_bytes(full=False))          # formato viejo, sin comisiones: igual se lee
    assert kind == "trade" and ev["creator"] is None and ev["real_token_reserves"] == 2


def test_decode_create_and_complete():
    c = DISC_CREATE + s("Pepe Lindo") + s("PEPEL") + s("https://x/y.json") + pk(5) + pk(6) + pk(7) + pk(8) + struct.pack("<q", 1_791_000_001)
    kind, ev = decode_event(c)
    assert kind == "create" and ev["symbol"] == "PEPEL" and ev["mint"] == b58(pk(5)) and ev["creator"] == b58(pk(8))
    k2, ev2 = decode_event(DISC_COMPLETE + pk(9) + pk(10) + pk(11) + struct.pack("<q", 7))
    assert k2 == "complete" and ev2["mint"] == b58(pk(10)) and ev2["ts_chain_s"] == 7


def test_garbage_is_ignored():
    assert decode_event(b"\x00" * 5) is None
    assert decode_event(DISC_TRADE + b"\x01\x02") is None
    assert events_from_logs(["Program log: hola", "Program data: !!!no-base64!!!"]) == []


class _Sink:
    def __init__(self):
        self.rows = []

    async def append(self, venue, table, row):
        self.rows.append((venue, table, row))


def test_handle_message_writes_rows_and_skips_failed_tx():
    rec = PumpfunRecorder(_Sink())
    logs = ["Program log: Instruction: Buy", "Program data: " + base64.b64encode(trade_bytes()).decode()]
    ok = {"jsonrpc": "2.0", "method": "logsNotification",
          "params": {"result": {"context": {"slot": 123}, "value": {"signature": "SIG", "err": None, "logs": logs}}}}
    bad = json.loads(json.dumps(ok))
    bad["params"]["result"]["value"]["err"] = {"InstructionError": [0, "x"]}
    assert asyncio.run(rec.handle_message(json.dumps(ok))) == 1
    assert asyncio.run(rec.handle_message(json.dumps(bad))) == 0
    venue, table, row = rec.sink.rows[0]
    assert venue == "pumpfun" and table == "pumpfun_trades" and row["slot"] == 123 and row["signature"] == "SIG"


def test_resolve_url_defaults_to_public_and_never_needs_key(tmp_path):
    url, src = resolve_url({"source": "helius"}, tmp_path)           # sin archivo de clave -> pública
    assert src == "public" and "api-key" not in url
    (tmp_path / ".env").write_text("HELIUS_API_KEY=abc\n")
    url, src = resolve_url({"source": "helius"}, tmp_path)
    assert src == "helius" and url.endswith("api-key=abc")


def test_env_file_parsing(tmp_path):
    from src.common.secret_loader import describe, get_secret, read_env_file
    (tmp_path / ".env").write_text("﻿# claves\nXAI_API_KEY=xai-123\nEMPTY=\nQUOTED=\"v\"\n", encoding="utf-8")
    assert read_env_file(tmp_path / ".env")["QUOTED"] == "v"
    assert get_secret("XAI_API_KEY", tmp_path) == "xai-123"
    d = describe("xai-123")
    assert d["empieza_con_xai"] and "xai-123" not in str(d)
