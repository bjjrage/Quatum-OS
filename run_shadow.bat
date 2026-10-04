@echo off
title Quant OS - STR-001 SHADOW + PAPER (dinero virtual, datos publicos)
cd /d "%~dp0"
echo Shadow STR-001: Polymarket vs Deribit. Log en data\shadow\
uv run python scripts\run_str001_shadow.py --paper
pause
