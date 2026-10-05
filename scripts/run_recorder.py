import argparse
import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

# Ensure root repository directory is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.collectors.manager import CollectorManager
from src.common.logger import setup_logger
from src.common.runtime_health import RuntimeHealth
from src.quality.acceptance import RuntimeManifest
from src.quality.fingerprint import compute_config_fingerprint

logger = setup_logger("main_service")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Market Data Recorder")
    parser.add_argument(
        "--new-run",
        action="store_true",
        help="Explicitly initiate a fresh runtime run after confirmed continuity gap",
    )
    parser.add_argument("--child", action="store_true", help="Internal: run under the restart supervisor")
    parser.add_argument("--pumpfun", action="store_true", help="Internal: run the pump.fun recorder process")
    parser.add_argument("--paper", action="store_true", help="Internal: run the paper-trading process")
    args = parser.parse_args()

    manager = CollectorManager()
    health = RuntimeHealth("markets_recorder")
    health.update("STARTING", started=True)
    loop = asyncio.get_running_loop()

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received termination signal. Shutting down gracefully...")
        stop_event.set()

    # Register OS signals for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows may not implement add_signal_handler for all signals
            pass

    manifest_path = Path("data/runtime/current_run.json")
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        git_sha = "UNKNOWN"

    fingerprint = compute_config_fingerprint()

    if args.new_run:
        manifest = RuntimeManifest.start_operator_new_run(
            filepath=manifest_path,
            pid=os.getpid(),
            git_sha=git_sha,
            config_fingerprint=fingerprint,
        )
        logger.info(
            f"Initialized explicit operator new run: {manifest.run_id} "
            f"(PID: {os.getpid()}, previous_run_id={manifest.previous_run_id}, reason={manifest.continuity_reason})"
        )
    else:
        manifest, was_resumed = RuntimeManifest.resume_or_create(
            filepath=manifest_path,
            pid=os.getpid(),
            git_sha=git_sha,
            config_fingerprint=fingerprint,
        )
        if was_resumed:
            logger.info(
                f"Resuming continuous acceptance run: {manifest.run_id} "
                f"(Elapsed: {manifest.elapsed_seconds():.1f}s)"
            )
        else:
            logger.info(
                f"Initialized new runtime manifest: {manifest.run_id} "
                f"(PID: {os.getpid()}, SHA: {git_sha[:8]})"
            )
        manifest.save(manifest_path)

    try:
        await manager.start()
        health.update("RUNNING", success=True)
        logger.info("Batch 0 Market Data Foundation is now live and recording.")
        
        heartbeat_counter = 0
        stop_file = Path("data/runtime/STOP_RECORDER")
        while not stop_event.is_set():
            await asyncio.sleep(1.0)
            if stop_file.exists():  # graceful stop requested from the cockpit
                logger.info("Stop requested from cockpit. Flushing and shutting down...")
                stop_event.set()
                break
            heartbeat_counter += 1
            if heartbeat_counter >= 30:
                manifest.update_heartbeat()
                manifest.save(manifest_path)
                health.update("RUNNING")
                heartbeat_counter = 0

    except (KeyboardInterrupt, SystemExit):
        logger.info("Interrupt received, stopping...")
    except Exception as exc:
        health.update("ERROR", error=exc)
        raise
    finally:
        await manager.stop()
        health.update("STOPPED")
        logger.info("Service shut down cleanly.")


RUNTIME_DIR = root_dir / "data" / "runtime"
STOP_FILE = RUNTIME_DIR / "STOP_RECORDER"
SUPERVISOR_PID = RUNTIME_DIR / "recorder_supervisor.pid"


def should_restart(returncode: int, stop_requested: bool, recent_restarts: int, max_per_hour: int = 12) -> bool:
    """Reiniciar solo si el recorder se cayó (código != 0), nadie pidió apagarlo y no está en un bucle de caídas."""
    return returncode != 0 and not stop_requested and recent_restarts < max_per_hour


def supervise(argv) -> int:
    """Vigilante: corre dos procesos hijos (mercados y pump.fun) y levanta de nuevo el que se caiga (p. ej. el
    'Fatal Python error' de Windows). Un apagado pedido desde el cockpit (archivo STOP_RECORDER) NO se reinicia."""
    import time as _time
    supervisor_health = RuntimeHealth("supervisor")
    supervisor_health.update("STARTING", started=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    SUPERVISOR_PID.write_text(str(os.getpid()), encoding="utf-8")
    base = [a for a in argv if a not in ("--child", "--pumpfun", "--paper")]
    me = str(Path(__file__).resolve())
    kinds = {"mercados": ["--child"], "pumpfun": ["--child", "--pumpfun"], "paper": ["--child", "--paper"]}
    procs, restarts = {}, {k: [] for k in kinds}

    def launch(kind, first):
        args = list(base) if first else [a for a in base if a != "--new-run"]   # al reiniciar, continuar el run
        if kind in ("pumpfun", "paper"):
            args = []
        procs[kind] = subprocess.Popen([sys.executable, me, *args, *kinds[kind]], cwd=str(root_dir))
        component = {"mercados": "markets_recorder", "paper": "paper_runtime", "pumpfun": "pumpfun_recorder"}[kind]
        RuntimeHealth(component).update("STARTING", started=True, pid=procs[kind].pid)

    try:
        for k in kinds:
            launch(k, True)
        supervisor_health.update("RUNNING", success=True)
        while procs:
            _time.sleep(1.0)
            supervisor_health.update("RUNNING")
            for kind, proc in list(procs.items()):
                rc = proc.poll()
                if rc is None:
                    component = {"mercados": "markets_recorder", "paper": "paper_runtime", "pumpfun": "pumpfun_recorder"}[kind]
                    RuntimeHealth(component).update("RUNNING", pid=proc.pid)
                    continue
                del procs[kind]
                now = _time.time()
                restarts[kind] = [t for t in restarts[kind] if now - t < 3600]
                stop = STOP_FILE.exists()
                component = {"mercados": "markets_recorder", "paper": "paper_runtime", "pumpfun": "pumpfun_recorder"}[kind]
                RuntimeHealth(component).update("STOPPED" if stop or rc == 0 else "ERROR", pid=None)
                if kind == "mercados" and (rc == 0 or stop):          # el principal terminó a pedido: apagar todo
                    for other in procs.values():
                        try:
                            other.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            other.terminate()
                    return rc
                if should_restart(rc if rc != 0 else 1, stop, len(restarts[kind])):
                    restarts[kind].append(now)
                    print(f"[vigilante] '{kind}' se cayó (código {rc}). Reiniciando en 5 s...", flush=True)
                    _time.sleep(5.0)
                    if not STOP_FILE.exists():
                        launch(kind, False)
                elif not stop:
                    print(f"[vigilante] '{kind}' se cayó {len(restarts[kind])} veces en una hora: no se reinicia más.", flush=True)
        return 0
    except KeyboardInterrupt:
        for p in procs.values():
            p.wait()
        return 0
    finally:
        supervisor_health.update("STOPPED")
        try:
            SUPERVISOR_PID.unlink()
        except OSError:
            pass


async def paper_main() -> None:
    """Proceso aparte: paper trading del flujo comprador V1 + fotos del libro de órdenes de las 65 cripto."""
    from config.settings import settings
    from src.common.storage_sink import StorageSink
    from src.paper.flujo_paper import run_paper
    from src.research.pyr_like import analysis_symbols
    log = setup_logger("paper_main")
    health = RuntimeHealth("paper_runtime")
    health.update("STARTING", started=True)
    sink = StorageSink(base_path=str(settings.storage.base_data_path),
                       flush_interval_sec=settings.storage.flush_interval_sec,
                       flush_row_threshold=settings.storage.flush_row_threshold,
                       compression=settings.storage.compression,
                       compression_level=settings.storage.compression_level,
                       manifest_enabled=settings.storage.manifest_enabled)
    await sink.start()
    symbols = [s for s in analysis_symbols(settings.binance.initial_calibration_sample_v0) if s != "PYRUSDT"]
    log.info(f"Paper flujo comprador: {len(symbols)} cripto.")
    try:
        health.update("RUNNING", success=True)
        await run_paper(symbols, sink=sink, stop_file=STOP_FILE)
    except Exception as exc:
        health.update("ERROR", error=exc)
        raise
    finally:
        await sink.stop()
        health.update("STOPPED")


async def pumpfun_main() -> None:
    """Proceso aparte para pump.fun: su propio guardado a disco, se apaga con el mismo archivo STOP_RECORDER."""
    from config.settings import settings
    from src.collectors.pumpfun_recorder import PumpfunRecorder
    from src.common.storage_sink import StorageSink
    log = setup_logger("pumpfun_main")
    health = RuntimeHealth("pumpfun_recorder")
    health.update("STARTING", started=True)
    sink = StorageSink(base_path=str(settings.storage.base_data_path),
                       flush_interval_sec=settings.storage.flush_interval_sec,
                       flush_row_threshold=settings.storage.flush_row_threshold,
                       compression=settings.storage.compression,
                       compression_level=settings.storage.compression_level,
                       manifest_enabled=settings.storage.manifest_enabled)
    await sink.start()
    rec = PumpfunRecorder(sink)
    await rec.start()
    health.update("RUNNING", success=True)
    log.info("pump.fun recorder corriendo (proceso aparte).")
    try:
        while not STOP_FILE.exists():
            await asyncio.sleep(1.0)
            health.update("RUNNING")
    finally:
        await rec.stop()
        await sink.stop()
        health.update("STOPPED")
        log.info("pump.fun recorder apagado y datos guardados.")


if __name__ == "__main__":
    if sys.platform == "win32":
        # El bucle por defecto de Windows (Proactor) tuvo caídas nativas ("Fatal Python error: PyEval_SaveThread")
        # con muchas conexiones a la vez. El bucle Selector es el clásico y estable para websockets/aiohttp.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    if "--child" not in sys.argv[1:]:
        sys.exit(supervise(sys.argv[1:]))
    try:
        if "--paper" in sys.argv[1:]:
            asyncio.run(paper_main())
        else:
            asyncio.run(pumpfun_main() if "--pumpfun" in sys.argv[1:] else main())
    except KeyboardInterrupt:
        sys.exit(0)
