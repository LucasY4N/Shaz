#!/usr/bin/env python3
"""
run.py — Unified Shaz AI Server Launcher (NEXUS v3.0)

Merges run_server.py (shaz.server) and run_server_new.py (backend.main).
Use --backend to choose which backend to run:
    python run.py                  # default: backend.main (refatorado)
    python run.py --backend old    # shaz.server (legado)

O Discord bot NÃO é iniciado automaticamente.
Use a interface web (http://localhost:PORT/app) para controlar o bot.
"""
import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path

# Fix encoding no Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Garante que o diretorio raiz esta no path
_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Shaz AI — NEXUS v3.0 Unified Server Launcher"
    )
    parser.add_argument(
        "--backend",
        choices=["new", "old"],
        default="new",
        help="Qual backend usar: 'new' (backend.main, refatorado) ou 'old' (shaz.server, legado)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Porta do servidor (default: 8765 ou do .env)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host do servidor (default: 127.0.0.1 ou do .env)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Não abrir o navegador automaticamente",
    )
    return parser.parse_args()


def open_browser(port: int):
    import time
    time.sleep(2.0)
    url = f"http://localhost:{port}/app"
    print(f"\n[Shaz] Abrindo {url} ...")
    webbrowser.open(url)


def run_new_backend(host: str, port: int, no_browser: bool):
    """Executa o backend refatorado (backend.main)."""
    from config.settings import get_settings

    settings = get_settings()

    # Command-line args sobrescrevem .env
    host = host or settings.server_host
    port = port or settings.server_port

    print("=" * 55)
    print("     Shaz AI — NEXUS v3.0 — Backend Refatorado")
    print("=" * 55)
    print(f"  API:     http://{host}:{port}/api")
    print(f"  App:     http://{host}:{port}/app")
    print(f"  WS:      ws://{host}:{port}/ws")
    print(f"  Docs:    http://{host}:{port}/docs")
    print(f"  Discord:  Não inicia automaticamente (via interface web)")
    print("  Ctrl+C para parar")
    print("=" * 55)

    if not no_browser:
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )


def run_old_backend(host: str, port: int, no_browser: bool):
    """Executa o backend legado (shaz.server)."""
    from shaz.server import app
    from shaz.utils.logger import logger

    # Command-line args sobrescrevem env vars
    port = port or int(os.environ.get("SHAZ_PORT", 8765))
    host = host or os.environ.get("SHAZ_HOST", "127.0.0.1")

    print("=" * 53)
    print("     Shaz AI -- NEXUS v3.0 -- Server Launcher (Legado)")
    print("=" * 53)
    print(f"  API:       http://{host}:{port}/api")
    print(f"  Web App:   http://{host}:{port}/app")
    print(f"  WebSocket: ws://{host}:{port}/ws")
    print(f"  Docs:      http://{host}:{port}/docs")
    print(f"  Discord:    Não inicia automaticamente (via interface web)")
    print("  Pressione CTRL+C para parar o servidor")
    print("=" * 53)

    if not no_browser:
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    args = parse_args()

    if args.backend == "new":
        run_new_backend(args.host, args.port, args.no_browser)
    else:
        run_old_backend(args.host, args.port, args.no_browser)