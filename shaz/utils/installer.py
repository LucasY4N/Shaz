"""
shaz/utils/installer.py
Instalador automático do Shaz AI.
Verifica dependências, instala pacotes faltantes, verifica FFmpeg,
modelos XTTS e Whisper.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from shaz.utils.helpers import is_ffmpeg_available, is_internet_available
from shaz.utils.logger import logger


class DependencyChecker:
    """
    Verificador e instalador automático de dependências.
    """

    REQUIRED_PACKAGES = [
        "PySide6",
        "faster-whisper",
        "edge-tts",
        "sounddevice",
        "soundfile",
        "pygame",
        "rich",
        "python-dotenv",
        "httpx",
        "openai",
        "groq",
        "google-genai",
        "requests",
        "pydantic",
    ]

    OPTIONAL_PACKAGES = [
        "TTS",
        "piper-tts",
        "psutil",
        "pyaudio",
        "numpy",
    ]

    @classmethod
    def check_python_version(cls) -> Tuple[bool, str]:
        """Verifica se a versão do Python é compatível."""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 11):
            return False, f"Python 3.11+ required (found {version.major}.{version.minor})"
        return True, f"Python {version.major}.{version.minor}.{version.micro}"

    @classmethod
    def check_package_installed(cls, package_name: str) -> bool:
        """Verifica se um pacote está instalado."""
        try:
            if package_name == "google-genai":
                import google.genai  # noqa
            elif package_name == "faster-whisper":
                import faster_whisper  # noqa
            elif package_name == "edge-tts":
                import edge_tts  # noqa
            elif package_name == "sounddevice":
                import sounddevice  # noqa
            elif package_name == "soundfile":
                import soundfile  # noqa
            elif package_name == "pygame":
                import pygame  # noqa
            elif package_name == "rich":
                import rich  # noqa
            elif package_name == "python-dotenv":
                import dotenv  # noqa
            elif package_name == "httpx":
                import httpx  # noqa
            elif package_name == "openai":
                import openai  # noqa
            elif package_name == "groq":
                import groq  # noqa
            elif package_name == "PySide6":
                import PySide6  # noqa
            elif package_name == "TTS":
                import TTS  # noqa
            elif package_name == "piper-tts":
                import piper  # noqa
            elif package_name == "psutil":
                import psutil  # noqa
            elif package_name == "pyaudio":
                import pyaudio  # noqa
            elif package_name == "requests":
                import requests  # noqa
            elif package_name == "pydantic":
                import pydantic  # noqa
            elif package_name == "numpy":
                import numpy  # noqa
            else:
                __import__(package_name)
            return True
        except ImportError:
            return False

    @classmethod
    def check_all_dependencies(cls) -> Dict[str, bool]:
        """Verifica todas as dependências e retorna status."""
        status = {}
        for pkg in cls.REQUIRED_PACKAGES:
            status[pkg] = cls.check_package_installed(pkg)
        for pkg in cls.OPTIONAL_PACKAGES:
            status[pkg] = cls.check_package_installed(pkg)
        return status

    @classmethod
    def install_package(cls, package_name: str, upgrade: bool = False) -> bool:
        """
        Instala um pacote via pip.

        Args:
            package_name: Nome do pacote
            upgrade: Se deve atualizar

        Returns:
            True se instalou com sucesso
        """
        try:
            cmd = [sys.executable, "-m", "pip", "install"]
            if upgrade:
                cmd.append("--upgrade")
            cmd.append(package_name)

            logger.system(f"Installing {package_name}...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                logger.system(f"{package_name} installed successfully")
                return True
            else:
                logger.error(f"Failed to install {package_name}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout installing {package_name}")
            return False
        except Exception as e:
            logger.error(f"Error installing {package_name}: {e}")
            return False

    @classmethod
    def install_missing_dependencies(cls) -> Tuple[int, int]:
        """
        Instala todas as dependências faltantes.

        Returns:
            Tuple (instalados, falhas)
        """
        installed = 0
        failed = 0

        if not is_internet_available():
            logger.error("No internet connection. Cannot install packages.")
            return installed, failed

        # Instala requeridos
        for pkg in cls.REQUIRED_PACKAGES:
            if not cls.check_package_installed(pkg):
                if cls.install_package(pkg):
                    installed += 1
                else:
                    failed += 1

        # Instala opcionais
        for pkg in cls.OPTIONAL_PACKAGES:
            if not cls.check_package_installed(pkg):
                logger.system(f"Optional package {pkg} not found. Attempting install...")
                if cls.install_package(pkg):
                    installed += 1
                # Falha em opcionais não conta como erro

        return installed, failed

    @classmethod
    def check_ffmpeg(cls) -> bool:
        """Verifica se FFmpeg está disponível."""
        available = is_ffmpeg_available()
        if not available:
            logger.warning(
                "FFmpeg not found. Audio processing may be limited.\n"
                "Install FFmpeg: https://ffmpeg.org/download.html"
            )
        return available

    @classmethod
    def check_whisper_models(cls) -> List[str]:
        """Verifica quais modelos Whisper estão disponíveis localmente."""
        models_dir = Path.home() / ".cache" / "whisper"
        if not models_dir.exists():
            return []

        available = []
        for model_size in ["tiny", "base", "small", "medium", "large"]:
            model_files = list(models_dir.glob(f"{model_size}*"))
            if model_files:
                available.append(model_size)

        return available

    @classmethod
    def run_full_check(cls) -> Dict[str, any]:
        """
        Executa verificação completa do sistema.

        Returns:
            Dicionário com status de todos os componentes
        """
        logger.system("Running full system check...")

        py_ok, py_ver = cls.check_python_version()
        deps = cls.check_all_dependencies()
        ffmpeg = cls.check_ffmpeg()
        whisper_models = cls.check_whisper_models()
        internet = is_internet_available()

        result = {
            "python_version": py_ver,
            "python_ok": py_ok,
            "ffmpeg": ffmpeg,
            "internet": internet,
            "dependencies": deps,
            "whisper_models": whisper_models,
            "required_installed": sum(1 for p in cls.REQUIRED_PACKAGES if deps.get(p)),
            "required_total": len(cls.REQUIRED_PACKAGES),
            "optional_installed": sum(1 for p in cls.OPTIONAL_PACKAGES if deps.get(p)),
            "optional_total": len(cls.OPTIONAL_PACKAGES),
        }

        # Log resumo
        logger.system(f"Python: {py_ver} {'✓' if py_ok else '✗'}")
        logger.system(f"FFmpeg: {'✓' if ffmpeg else '✗'}")
        logger.system(f"Internet: {'✓' if internet else '✗'}")
        logger.system(f"Dependencies: {result['required_installed']}/{result['required_total']} required, {result['optional_installed']}/{result['optional_total']} optional")

        for pkg, installed in deps.items():
            status = "✓" if installed else "✗"
            logger.system(f"  {status} {pkg}")

        if whisper_models:
            logger.system(f"Whisper models cached: {', '.join(whisper_models)}")

        return result


class Installer:
    """
    Instalador automático completo do Shaz AI.
    """

    @staticmethod
    def install() -> int:
        """
        Executa instalação completa.

        Returns:
            Código de saída (0 = sucesso, 1 = falha)
        """
        from rich.console import Console
        from rich.panel import Panel
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TextColumn,
            TimeElapsedColumn,
        )

        console = Console()

        console.print(Panel.fit(
            "[bold cyan]🚀 Shaz AI - Instalador Automático[/bold cyan]\n"
            "[dim]Verificando e instalando dependências...[/dim]",
            border_style="cyan",
        ))

        # 1. Verificar Python
        py_ok, py_ver = DependencyChecker.check_python_version()
        if not py_ok:
            console.print(f"[red]✗ {py_ver}[/red]")
            return 1
        console.print(f"[green]✓ {py_ver}[/green]")

        # 2. Verificar internet
        internet = is_internet_available()
        if not internet:
            console.print("[yellow]⚠ Sem internet. Apenas dependências já instaladas serão usadas.[/yellow]")

        # 3. Checar dependências com progresso
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Verificando dependências...", total=len(DependencyChecker.REQUIRED_PACKAGES) + len(DependencyChecker.OPTIONAL_PACKAGES))

            deps = {}
            for pkg in DependencyChecker.REQUIRED_PACKAGES + DependencyChecker.OPTIONAL_PACKAGES:
                deps[pkg] = DependencyChecker.check_package_installed(pkg)
                progress.advance(task)

        # 4. Instalar faltantes
        missing = [p for p, installed in deps.items() if not installed]
        if missing and internet:
            console.print(f"\n[cyan]Instalando {len(missing)} pacotes faltantes...[/cyan]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Instalando...", total=len(missing))

                for pkg in missing:
                    progress.update(task, description=f"[cyan]Instalando {pkg}...[/cyan]")
                    success = DependencyChecker.install_package(pkg)
                    if success:
                        console.print(f"  [green]✓ {pkg}[/green]")
                    else:
                        console.print(f"  [red]✗ {pkg}[/red]")
                    progress.advance(task)

        # 5. Verificar FFmpeg
        if not DependencyChecker.check_ffmpeg():
            console.print("[yellow]⚠ FFmpeg não encontrado. Baixe de: https://ffmpeg.org/download.html[/yellow]")

        # 6. Verificar modelos Whisper
        models = DependencyChecker.check_whisper_models()
        if models:
            console.print(f"[green]✓ Modelos Whisper: {', '.join(models)}[/green]")

        # 7. Resumo final
        installed_count = sum(1 for p in DependencyChecker.REQUIRED_PACKAGES if DependencyChecker.check_package_installed(p))
        total_required = len(DependencyChecker.REQUIRED_PACKAGES)

        if installed_count == total_required:
            console.print(Panel.fit(
                "[bold green]✅ Instalação concluída com sucesso![/bold green]\n"
                f"Pacotes requeridos: {installed_count}/{total_required}\n\n"
                "[cyan]Para iniciar o Shaz AI:[/cyan]\n"
                "  python main.py\n"
                "  python -m shaz\n\n"
                "[dim]Configure suas chaves de API no arquivo .env[/dim]",
                border_style="green",
            ))
            return 0
        else:
            console.print(Panel.fit(
                f"[bold yellow]⚠ Instalação parcial: {installed_count}/{total_required}[/bold yellow]\n"
                "Alguns pacotes podem precisar de instalação manual:\n"
                f"  pip install {' '.join(DependencyChecker.REQUIRED_PACKAGES)}\n\n"
                "[dim]Veja README.md para instruções detalhadas[/dim]",
                border_style="yellow",
            ))
            return 1


# ─── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.exit(Installer.install())


__all__ = ["DependencyChecker", "Installer"]