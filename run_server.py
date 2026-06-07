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

# Garante que o diretório raiz está no path
_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from shaz.server import app
from shaz.utils.logger import logger

PORT = int(os.environ.get("SHAZ_PORT", 8765))
HOST = os.environ.get("SHAZ_HOST", "127.0.0.1")  # localhost only for security


def open_browser():
    """Abre o navegador após um pequeno delay."""
    import time
    time.sleep(2)
    url = f"http://localhost:{PORT}/app"
    print(f"\n🌐 Abrindo {url} ...")
    webbrowser.open(url)


if __name__ == "__main__":
    print(f"╔═══════════════════════════════════════════════════╗")
    print(f"║     Shaz AI — NEXUS v3.0 — Server Launcher       ║")
    print(f"╠═══════════════════════════════════════════════════╣")
    print(f"║  API:     http://localhost:{PORT}/api             ║")
    print(f"║  Web App: http://localhost:{PORT}/app             ║")
    print(f"║  WebSocket: ws://localhost:{PORT}/ws              ║")
    print(f"║  Docs:    http://localhost:{PORT}/docs            ║")
    print(f"║                                                   ║")
    print(f"║  Pressione CTRL+C para parar o servidor           ║")
    print(f"╚═══════════════════════════════════════════════════╝")
    
    # Abre o navegador em thread separada
    threading.Thread(target=open_browser, daemon=True).start()
    
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")