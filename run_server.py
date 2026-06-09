#!/usr/bin/env python3
"""
run_server.py
Inicia o servidor HTTP + WebSocket do Shaz AI.
Abre automaticamente o navegador no http://localhost:8765/app
"""
import os
import sys
import threading
import webbrowser
from pathlib import Path

# Fix encoding no Windows (cp1252 nao suporta box-drawing chars)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Garante que o diretorio raiz esta no path
_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from shaz.server import app
from shaz.utils.logger import logger

PORT = int(os.environ.get("SHAZ_PORT", 8765))
HOST = os.environ.get("SHAZ_HOST", "127.0.0.1")  # localhost only for security


def open_browser():
    """Abre o navegador apos um pequeno delay."""
    import time
    time.sleep(2)
    url = f"http://localhost:{PORT}/app"
    print(f"\n[Shaz] Abrindo {url} ...")
    webbrowser.open(url)


if __name__ == "__main__":
    print("=" * 53)
    print("     Shaz AI -- NEXUS v3.0 -- Server Launcher")
    print("=" * 53)
    print(f"  API:       http://localhost:{PORT}/api")
    print(f"  Web App:   http://localhost:{PORT}/app")
    print(f"  WebSocket: ws://localhost:{PORT}/ws")
    print(f"  Docs:      http://localhost:{PORT}/docs")
    print("  Pressione CTRL+C para parar o servidor")
    print("=" * 53)

    # Abre o navegador em thread separada
    threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")