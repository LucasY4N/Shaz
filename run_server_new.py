#!/usr/bin/env python3
"""
run_server.py (novo)
Inicia o servidor Shaz AI com a nova estrutura backend/.
"""
import sys
import os
import threading
import webbrowser
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Adiciona root ao path
_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from config.settings import get_settings

settings = get_settings()
PORT = settings.server_port
HOST = settings.server_host


def open_browser():
    import time
    time.sleep(2.0)
    webbrowser.open(f"http://localhost:{PORT}/app")


if __name__ == "__main__":
    print("=" * 55)
    print("     Shaz AI — NEXUS v3.0 — Backend Refatorado")
    print("=" * 55)
    print(f"  API:     http://localhost:{PORT}/api")
    print(f"  App:     http://localhost:{PORT}/app")
    print(f"  WS:      ws://localhost:{PORT}/ws")
    print(f"  Docs:    http://localhost:{PORT}/docs")
    print(f"  Redoc:   http://localhost:{PORT}/redoc")
    print("  Ctrl+C para parar")
    print("=" * 55)

    threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
    )
