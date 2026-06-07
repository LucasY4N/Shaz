"""
shaz/main.py
Ponto de entrada principal do Shaz AI.
Inicializa: Config -> Memoria -> Personalidade -> API -> Voz -> UI -> Brain.
"""
from __future__ import annotations

import asyncio
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Optional

_current_dir = Path(__file__).parent.parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from shaz.core.brain import ShazBrain
from shaz.core.config import Config
from shaz.core.memory import Memory
from shaz.core.personality import Personality
from shaz.utils.helpers import is_internet_available, get_system_info
from shaz.utils.logger import logger, setup_logger


class ShazApp:
    """
    Aplicacao principal Shaz AI.
    """

    def __init__(self) -> None:
        self._config: Optional[Config] = None
        self._memory: Optional[Memory] = None
        self._personality: Optional[Personality] = None
        self._brain: Optional[ShazBrain] = None
        self._initialized = False
        self._voice_task: Optional[asyncio.Task] = None

    def initialize(self) -> bool:
        try:
            logger.system("Inicializando Shaz AI...")

            self._config = Config()
            logger.system(f"Config carregada | v{self._config.app_version}")

            setup_logger(
                log_level=self._config.log_level,
                log_dir=self._config.logs_path,
                max_file_size_mb=self._config.log_max_file_size_mb,
                retention_days=self._config.log_retention_days,
            )

            db_path = str(self._config.data_path / "memory.db")
            self._memory = Memory(db_path)
            logger.system(f"Memoria carregada | db={db_path}")

            self._personality = Personality(self._memory)
            logger.system("Personalidade carregada")

            sys_info = get_system_info()
            logger.system(f"Sistema: {sys_info.get('platform', 'unknown')}")

            internet = is_internet_available()
            if not internet:
                logger.warning("Sem conexao com internet. Alguns recursos podem ser limitados.")

            self._brain = ShazBrain(
                config=self._config,
                memory=self._memory,
                personality=self._personality,
            )

            self._initialized = True
            logger.system("Shaz AI inicializada com sucesso!")
            return True

        except Exception as e:
            from rich.console import Console
            Console().print(f"[red]Erro ao inicializar Shaz AI: {e}[/red]")
            import traceback
            traceback.print_exc()
            return False

    async def process_message(self, text: str) -> str:
        if not self._brain:
            return "Sistema nao inicializado."
        return await self._brain.process_message(text)

    async def start_voice_loop(self) -> None:
        """Inicia o loop de voz."""
        if not self._brain:
            logger.error("Brain nao inicializado")
            return
        self._voice_task = asyncio.create_task(self._brain.process_voice())

    def stop_voice(self) -> None:
        """Para o modo de voz."""
        if self._brain:
            self._brain.stop_voice_mode()
        if self._voice_task and not self._voice_task.done():
            self._voice_task.cancel()

    def get_brain(self) -> Optional[ShazBrain]:
        return self._brain

    def shutdown(self) -> None:
        logger.system("Desligando Shaz AI...")
        self.stop_voice()
        if self._memory:
            self._memory.close()
        logger.system("Shaz AI desligada.")
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized


_app: Optional[ShazApp] = None


def get_app() -> ShazApp:
    global _app
    if _app is None:
        _app = ShazApp()
    return _app


def run_desktop() -> None:
    """
    Executa o modo Desktop com console.
    Abre a interface Shaz + console mostrando todo o processo em tempo real.
    """
    import sys as _sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QObject, QTimer, Signal, Slot

    # Inicializa a aplicacao
    app = get_app()
    if not app.initialize():
        from rich.console import Console
        Console().print("[red]Falha na inicializacao[/red]")
        _sys.exit(1)

    # QApplication
    qt_app = QApplication(_sys.argv)
    qt_app.setApplicationName("Shaz")
    qt_app.setApplicationVersion("1.0.0")
    qt_app.setStyle("Fusion")

    from shaz.ui.dashboard import Dashboard

    brain = app.get_brain()
    dashboard = Dashboard(config=brain.config if brain else None)

    # Conecta eventos do chat
    chat = dashboard.get_chat_widget()

    class UiBridge(QObject):
        status_changed = Signal(str)
        assistant_response = Signal(str)

        def __init__(self, dashboard_widget, chat_widget) -> None:
            super().__init__()
            self._dashboard_widget = dashboard_widget
            self._chat_widget = chat_widget

        @Slot(str)
        def apply_status(self, status: str) -> None:
            self._dashboard_widget.update_status(status)

        @Slot(str)
        def add_assistant_response(self, response: str) -> None:
            self._chat_widget.add_message("assistant", response)

    ui_bridge = UiBridge(dashboard, chat)
    ui_bridge.status_changed.connect(ui_bridge.apply_status)
    ui_bridge.assistant_response.connect(ui_bridge.add_assistant_response)

    async def async_send(text: str) -> str:
        return await brain.process_message(text) if brain else "Brain indisponivel"

    def on_send(text: str) -> None:
        """Dispara quando usuario envia mensagem pelo chat."""
        def run_message() -> None:
            try:
                asyncio.run(async_send(text))
            except Exception as e:
                logger.error(f"[UI] Error processing chat message: {e}")
                ui_bridge.assistant_response.emit(
                    f"Desculpe, ocorreu um erro ao processar sua mensagem: {e}"
                )

        threading.Thread(
            target=run_message,
            name="ShazChatMessage",
            daemon=True,
        ).start()

    chat.set_on_send(on_send)

    # Evento de voz: quando ativar o microfone no chat
    voice_thread: Optional[threading.Thread] = None

    def run_voice_loop() -> None:
        if not brain:
            return
        try:
            asyncio.run(brain.process_voice())
        except Exception as e:
            logger.error(f"[UI] Voice loop error: {e}")
            ui_bridge.assistant_response.emit(f"Erro no modo de voz: {e}")
        finally:
            ui_bridge.status_changed.emit("online")

    def on_voice_activate():
        """Ativou o modo de voz."""
        nonlocal voice_thread
        if brain:
            logger.voice("Modo de voz ATIVADO pelo usuario")
            ui_bridge.status_changed.emit("listening")
            if voice_thread and voice_thread.is_alive():
                return
            voice_thread = threading.Thread(
                target=run_voice_loop,
                name="ShazVoiceLoop",
                daemon=True,
            )
            voice_thread.start()

    def on_voice_deactivate():
        """Desativou o modo de voz."""
        if brain:
            brain.stop_voice_mode()
            ui_bridge.status_changed.emit("online")
            logger.voice("Modo de voz DESATIVADO pelo usuario")

    chat.voice_activated.connect(on_voice_activate)
    chat.voice_deactivated.connect(on_voice_deactivate)

    # Evento de ligar/desligar pelo dashboard
    def on_power_toggle(on: bool) -> None:
        """Liga ou desliga o sistema."""
        if on:
            dashboard.update_status("online")
            logger.system("Sistema ATIVADO pelo usuario")
            # Mostra mensagem inicial no terminal
            logger.system("Shaz AI pronta para uso!")
            logger.system("Provedores disponiveis: " + ", ".join(brain.api.available_providers) if brain else "N/A")
            logger.system("TTS: Edge TTS (FranciscaNeural)")
            logger.system("STT: Faster-Whisper (modelo base)")
        else:
            if brain:
                brain.stop_voice_mode()
            dashboard.update_status("offline")
            logger.system("Sistema DESATIVADO pelo usuario")

    def on_restart() -> None:
        """Reinicia o sistema."""
        logger.system("Reiniciando sistema...")
        if brain:
            brain.stop_voice_mode()
            brain.clear_history()
        chat.clear()
        dashboard.update_status("online")
        logger.system("Sistema reiniciado. Pronto para uso!")

    if brain:
        dashboard.set_on_power_toggle(on_power_toggle)
        dashboard.set_on_restart(on_restart)
        brain.set_on_status_change(ui_bridge.status_changed.emit)
        brain.set_on_response(ui_bridge.assistant_response.emit)

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    dashboard.show()
    logger.system("Interface Shaz iniciada")
    logger.system("Pressione LIGAR para ativar o sistema")

    # Timer para manter o event loop rodando
    timer = QTimer()
    timer.start(100)

    exit_code = qt_app.exec()
    app.shutdown()
    _sys.exit(exit_code)


def run_cli() -> None:
    """Executa o modo CLI."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt

    console = Console()
    app = get_app()

    if not app.initialize():
        console.print("[red]Falha na inicializacao. Verifique os logs.[/red]")
        sys.exit(1)

    console.print(Panel.fit(
        "[bold green]Shaz AI - Terminal Interativo[/bold green]\n"
        "[dim]Digite sua mensagem ou comandos:[/dim]\n"
        "  sair   - Encerra o programa\n"
        "  voz    - Ativa modo de voz\n"
        "  parar  - Para modo de voz\n"
        "  limpar - Limpa historico\n"
        "  ajuda  - Mostra comandos",
        border_style="green",
    ))

    try:
        while True:
            text = Prompt.ask("[bold cyan]Voce[/bold cyan]")
            cmd = text.lower().strip()

            if cmd in ["sair", "exit", "quit", "q"]:
                break
            elif cmd == "voz":
                console.print("[green]Ativando modo de voz... Fale algo (Ctrl+C para parar)[/green]")
                asyncio.run(app.get_brain().process_voice())
            elif cmd == "parar":
                app.stop_voice()
                console.print("[yellow]Modo de voz parado[/yellow]")
            elif cmd == "limpar":
                if app.get_brain():
                    app.get_brain().clear_history()
                console.print("[yellow]Historico limpo[/yellow]")
            elif cmd == "ajuda" or cmd == "help":
                console.print(Panel.fit(
                    "[bold]Comandos disponiveis:[/bold]\n"
                    "  sair   - Encerra\n"
                    "  voz    - Ativa modo de voz\n"
                    "  parar  - Para modo de voz\n"
                    "  limpar - Limpa historico\n"
                    "  ajuda  - Mostra esta mensagem",
                    title="Ajuda",
                ))
            else:
                response = asyncio.run(app.process_message(text))
                console.print(Panel(response, title="[bold green]Shaz[/bold green]", border_style="green"))

    except KeyboardInterrupt:
        console.print("\n[yellow]Encerrando...[/yellow]")
    finally:
        app.shutdown()


# ─── Entry Points ────────────────────────────────────────────────────────

def main_cli() -> None:
    run_cli()


def main_desktop() -> None:
    run_desktop()


if __name__ == "__main__":
    import sys as _sys

    if "--cli" in _sys.argv:
        run_cli()
    else:
        try:
            import PySide6  # noqa: F401
            run_desktop()
        except ImportError:
            print("PySide6 nao instalado. Use --cli para modo terminal ou execute o instalador:")
            print("  python main.py --install")
            print("  python main.py --cli")
            _sys.exit(1)
