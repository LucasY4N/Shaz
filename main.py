#!/usr/bin/env python3
"""
Shaz AI - Assistente Virtual com Voz
Ponto de entrada.

Uso:
    python main.py              # Modo Desktop (interface Shaz + console)
    python main.py --cli        # Modo Terminal
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shaz.main import main_desktop, main_cli

if __name__ == "__main__":
    if "--cli" in sys.argv:
        main_cli()
    else:
        try:
            import PySide6  # noqa: F401
            main_desktop()
        except ImportError:
            print("PySide6 nao instalado. Use: python main.py --cli")
            sys.exit(1)