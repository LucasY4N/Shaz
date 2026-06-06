"""
shaz/ui/dashboard.py
Dashboard principal do Shaz AI com PySide6.
Layout: STATUS | LOGS | TERMINAL | CHAT | CONTROLS
Tema moderno, profissional, futurista e responsivo.
"""
from __future__ import annotations

import asyncio
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QFont, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from shaz.core.config import Config
from shaz.ui.chat import ChatWidget
from shaz.ui.terminal import TerminalWidget
from shaz.utils.logger import logger


# ─── Status Indicator ────────────────────────────────────────────────────

class StatusWidget(QFrame):
    """
    Widget que mostra o status atual do sistema.
    Cores: Verde (Online), Amarelo (Processando), Azul (Ouvindo),
    Laranja (Falando), Vermelho (Offline)
    """

    STATUS_STYLES = {
        "online": """
            QFrame { background-color: #0a2a0a; border: 1px solid #00ff7f; border-radius: 8px; }
            QLabel#status_icon { color: #00ff7f; font-size: 20px; }
            QLabel#status_text { color: #00ff7f; font-size: 12px; font-weight: bold; }
        """,
        "processing": """
            QFrame { background-color: #2a2a00; border: 1px solid #ffd700; border-radius: 8px; }
            QLabel#status_icon { color: #ffd700; font-size: 20px; }
            QLabel#status_text { color: #ffd700; font-size: 12px; font-weight: bold; }
        """,
        "listening": """
            QFrame { background-color: #002a3a; border: 1px solid #00bfff; border-radius: 8px; }
            QLabel#status_icon { color: #00bfff; font-size: 20px; }
            QLabel#status_text { color: #00bfff; font-size: 12px; font-weight: bold; }
        """,
        "speaking": """
            QFrame { background-color: #2a1a00; border: 1px solid #ff8c00; border-radius: 8px; }
            QLabel#status_icon { color: #ff8c00; font-size: 20px; }
            QLabel#status_text { color: #ff8c00; font-size: 12px; font-weight: bold; }
        """,
        "offline": """
            QFrame { background-color: #2a0000; border: 1px solid #ff4444; border-radius: 8px; }
            QLabel#status_icon { color: #ff4444; font-size: 20px; }
            QLabel#status_text { color: #ff4444; font-size: 12px; font-weight: bold; }
        """,
    }

    STATUS_ICONS = {
        "online": "🟢",
        "processing": "🟡",
        "listening": "🔵",
        "speaking": "🟠",
        "offline": "🔴",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._status = "offline"
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        self._icon_label = QLabel(self.STATUS_ICONS["offline"])
        self._icon_label.setObjectName("status_icon")

        self._text_label = QLabel("Offline")
        self._text_label.setObjectName("status_text")

        layout.addWidget(self._icon_label)
        layout.addWidget(self._text_label)

        self.set_status("offline")

    def set_status(self, status: str) -> None:
        """Atualiza o status visual."""
        if status not in self.STATUS_STYLES:
            status = "offline"
        self._status = status
        self.setStyleSheet(self.STATUS_STYLES[status])
        self._icon_label.setText(self.STATUS_ICONS[status])
        self._text_label.setText(status.capitalize())

    @property
    def status(self) -> str:
        return self._status


# ─── Metrics Panel ──────────────────────────────────────────────────────

class MetricsWidget(QFrame):
    """Widget que exibe metricas do sistema."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #1a1a2e;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel {
                color: #8b949e;
                font-size: 11px;
            }
            QLabel#value {
                color: #00ff7f;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        layout = QGridLayout(self)
        layout.setSpacing(12)

        metrics = [
            ("CPU", "0%", 0, 0),
            ("RAM", "0 MB", 0, 2),
            ("Modelo", "N/A", 1, 0),
            ("Provedor", "N/A", 1, 2),
            ("Conversas", "0", 2, 0),
            ("Memorias", "0", 2, 2),
        ]

        for label, value, row, col in metrics:
            lbl = QLabel(label.upper())
            val = QLabel(value)
            val.setObjectName("value")
            layout.addWidget(lbl, row, col)
            layout.addWidget(val, row, col + 1)

        self._labels = {}
        for label, value, row, col in metrics:
            self._labels[label.lower()] = layout.itemAtPosition(row, col + 1).widget()

    def update_metric(self, key: str, value: str) -> None:
        if key in self._labels:
            self._labels[key].setText(value)


# ─── Control Buttons ────────────────────────────────────────────────────

class ControlButtons(QFrame):
    """Botoes de controle: Ligar, Desligar, Reiniciar."""

    power_toggled = Signal(bool)
    restart_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._is_on = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #1a1a2e;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        btn_style_off = """
            QPushButton {
                background-color: #2a2a2a; color: #666; border: none;
                border-radius: 8px; padding: 12px 24px; font-size: 13px; font-weight: bold;
            }
        """
        btn_style_power = """
            QPushButton {
                background-color: #00ff7f; color: #0d1117; border: none;
                border-radius: 8px; padding: 12px 24px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #00cc66; }
            QPushButton:checked { background-color: #ff4444; color: white; }
        """
        btn_style_restart = """
            QPushButton {
                background-color: #1a3a5c; color: #e0e0e0; border: none;
                border-radius: 8px; padding: 12px 24px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2a4a6c; }
        """

        self._power_btn = QPushButton("LIGAR")
        self._power_btn.setStyleSheet(btn_style_power)
        self._power_btn.setCheckable(True)
        self._power_btn.toggled.connect(self._on_power_toggle)
        layout.addWidget(self._power_btn)

        self._restart_btn = QPushButton("REINICIAR")
        self._restart_btn.setStyleSheet(btn_style_restart)
        self._restart_btn.clicked.connect(self.restart_requested.emit)
        layout.addWidget(self._restart_btn)

    def _on_power_toggle(self, checked: bool) -> None:
        self._is_on = checked
        self._power_btn.setText("DESLIGAR" if checked else "LIGAR")
        self.power_toggled.emit(checked)

    @property
    def is_on(self) -> bool:
        return self._is_on

    def set_power(self, on: bool) -> None:
        self._power_btn.setChecked(on)


# ─── Main Dashboard ─────────────────────────────────────────────────────

class Dashboard(QMainWindow):
    """
    Dashboard principal do Shaz AI.
    Layout completo com status, logs, terminal, chat e controles.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        super().__init__()
        self._config = config or Config()
        self._shutdown_requested = False
        self._on_power_toggle: Optional[Callable[[bool], Any]] = None
        self._on_restart: Optional[Callable[[], Any]] = None

        self._setup_window()
        self._setup_menu()
        self._setup_central_widget()
        self._setup_status_bar()
        self._setup_timers()

        logger.system("Dashboard initialized")
        self.update_status("online")

    def _setup_window(self) -> None:
        """Configura a janela principal."""
        self.setWindowTitle(f"Shaz AI - {self._config.app_version}")
        self.setMinimumSize(800, 600)
        self.resize(self._config.window_width, self._config.window_height)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0d1117;
            }
            QWidget {
                background-color: #0d1117;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QSplitter::handle {
                background-color: #1a1a2e;
                width: 2px;
            }
            QTabWidget::pane {
                background-color: #0d1117;
                border: 1px solid #1a1a2e;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #161b22;
                color: #8b949e;
                padding: 8px 16px;
                border: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0d1117;
                color: #00ff7f;
                border-bottom: 2px solid #00ff7f;
            }
            QTabBar::tab:hover {
                background-color: #1a1a2e;
                color: #e0e0e0;
            }
            QScrollBar:vertical {
                background-color: #0d1117;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #1a1a2e;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #2a2a3e;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def _setup_menu(self) -> None:
        """Configura a barra de menu."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #161b22;
                color: #e0e0e0;
                border-bottom: 1px solid #1a1a2e;
                padding: 2px;
            }
            QMenuBar::item:selected {
                background-color: #1a3a5c;
            }
            QMenu {
                background-color: #161b22;
                color: #e0e0e0;
                border: 1px solid #1a1a2e;
            }
            QMenu::item:selected {
                background-color: #1a3a5c;
            }
        """)

        # Arquivo
        file_menu = menubar.addMenu("Arquivo")
        self._add_action(file_menu, "Reiniciar", self._on_restart_action, "Ctrl+R")
        self._add_action(file_menu, "Sair", self.close, "Ctrl+Q")

        # Exibir
        view_menu = menubar.addMenu("Exibir")
        self._add_action(view_menu, "Limpar Terminal", self._clear_terminal, "Ctrl+L")
        self._add_action(view_menu, "Limpar Chat", self._clear_chat, "Ctrl+Shift+L")

        # Ajuda
        help_menu = menubar.addMenu("Ajuda")
        self._add_action(help_menu, "Sobre", self._show_about)

    def _add_action(self, menu, text, callback, shortcut=None):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        menu.addAction(action)

    def _setup_central_widget(self) -> None:
        """Configura o widget central com todo o layout."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(8)

        # Header
        header = QLabel("SHAZ AI")
        header.setStyleSheet("""
            QLabel {
                color: #00ff7f;
                font-size: 24px;
                font-weight: bold;
                padding: 4px 0;
            }
        """)
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # Status bar
        self._status_widget = StatusWidget()
        main_layout.addWidget(self._status_widget)

        # Splitter principal
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(2)

        # Top section: Metrics + Tabs (Logs, Terminal)
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        # Metrics row
        self._metrics = MetricsWidget()
        top_layout.addWidget(self._metrics)

        # Tabs: Logs, Terminal
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.North)

        self._terminal = TerminalWidget()
        tabs.addTab(self._terminal, "Terminal")

        top_layout.addWidget(tabs)
        splitter.addWidget(top_widget)

        # Bottom section: Chat + Controls
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)

        self._chat = ChatWidget()
        bottom_layout.addWidget(self._chat)

        # Control buttons
        self._controls = ControlButtons()
        self._controls.power_toggled.connect(self._on_power_toggle_internal)
        self._controls.restart_requested.connect(self._on_restart_internal)
        bottom_layout.addWidget(self._controls)

        splitter.addWidget(bottom_widget)

        # Set proportions (60% top, 40% bottom)
        splitter.setSizes([400, 300])
        main_layout.addWidget(splitter)

    def _setup_status_bar(self) -> None:
        """Configura a barra de status."""
        status = QStatusBar()
        status.setStyleSheet("""
            QStatusBar {
                background-color: #161b22;
                color: #8b949e;
                border-top: 1px solid #1a1a2e;
                font-size: 11px;
                padding: 2px 8px;
            }
        """)
        self._status_label = QLabel("Pronto")
        status.addWidget(self._status_label)

        provider_label = QLabel(f"Provedor: {self._config.llm_provider}")
        status.addPermanentWidget(provider_label)

        version_label = QLabel(f"v{self._config.app_version}")
        status.addPermanentWidget(version_label)

        self.setStatusBar(status)

    def _setup_timers(self) -> None:
        """Configura timers."""
        self._ui_timer = QTimer()
        self._ui_timer.timeout.connect(self._update_ui)
        self._ui_timer.start(2000)

    def _update_ui(self) -> None:
        """Atualiza periodicamente a interface."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            self._metrics.update_metric("cpu", f"{cpu:.0f}%")
            self._metrics.update_metric("ram", f"{mem.used / 1024 / 1024:.0f} MB")
        except ImportError:
            pass

    def _on_power_toggle_internal(self, on: bool) -> None:
        """Callback interno para toggle de energia."""
        if self._on_power_toggle:
            self._on_power_toggle(on)
        if on:
            self.update_status("online")
            self._status_label.setText("Sistema ativo")
        else:
            self.update_status("offline")
            self._status_label.setText("Sistema desligado")

    def _on_restart_internal(self) -> None:
        """Callback interno para restart."""
        if self._on_restart:
            self._on_restart()
        self._status_label.setText("Reiniciando...")

    def _on_restart_action(self) -> None:
        """Acao de reiniciar pelo menu."""
        self._controls.set_power(False)
        self._controls.set_power(True)
        self._on_restart_internal()

    def _clear_terminal(self) -> None:
        """Limpa o terminal."""
        self._terminal.clear()

    def _clear_chat(self) -> None:
        """Limpa o chat."""
        self._chat.clear()

    def _show_about(self) -> None:
        """Mostra dialogo sobre."""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "Sobre o Shaz AI",
            f"<h2>Shaz AI v{self._config.app_version}</h2>"
            "<p>Assistente virtual com inteligencia artificial, "
            "reconhecimento de voz, sintese de voz, memoria persistente "
            "e personalidade propria.</p>"
            "<p>Pyxis-7 &copy; 2026</p>",
        )

    def set_on_power_toggle(self, callback: Callable[[bool], Any]) -> None:
        """Define callback para toggle de energia."""
        self._on_power_toggle = callback

    def set_on_restart(self, callback: Callable[[], Any]) -> None:
        """Define callback para restart."""
        self._on_restart = callback

    def update_status(self, status: str) -> None:
        """Atualiza o status visual do dashboard."""
        self._status_widget.set_status(status)

    def update_metric(self, key: str, value: str) -> None:
        """Atualiza uma metrica."""
        self._metrics.update_metric(key, value)

    def get_chat_widget(self) -> ChatWidget:
        """Retorna o widget de chat."""
        return self._chat

    def get_terminal_widget(self) -> TerminalWidget:
        """Retorna o widget de terminal."""
        return self._terminal

    def closeEvent(self, event) -> None:
        """Evento de fechamento da janela."""
        self._shutdown_requested = True
        self._ui_timer.stop()

        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self, "Sair",
            "Deseja realmente sair do Shaz AI?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            logger.system("Dashboard closed by user")
            event.accept()
        else:
            self._shutdown_requested = False
            self._ui_timer.start(2000)
            event.ignore()