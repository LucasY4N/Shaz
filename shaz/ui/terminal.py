"""
shaz/ui/terminal.py
Widget de terminal embutido para o Shaz AI.
Exibe logs em tempo real com categorias coloridas, status e processos.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

from shaz.utils.logger import LogEmitter

CATEGORY_COLORS = {
    "INFO": "#00CED1",
    "VOICE": "#FF00FF",
    "STT": "#FFD700",
    "TTS": "#4169E1",
    "MEMORY": "#00FF7F",
    "API": "#FFFFFF",
    "SYSTEM": "#696969",
    "ERROR": "#FF4444",
    "DEBUG": "#666666",
    "WARNING": "#FF8C00",
}


class LogEntry:
    """Representa uma entrada de log."""

    def __init__(self, record: logging.LogRecord) -> None:
        self.timestamp = datetime.fromtimestamp(record.created)
        self.level = record.levelname
        self.message = record.getMessage()
        self.color = CATEGORY_COLORS.get(self.level, "#FFFFFF")


def _escape(text: str) -> str:
    """Escapa caracteres especiais HTML."""
    return text.replace("&", "&").replace("<", "<").replace(">", ">")


class TerminalWidget(QWidget):
    """
    Widget de terminal que exibe logs em tempo real.
    Suporta categorias coloridas, auto-scroll e filtros.
    """

    log_received = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._max_lines = 1000
        self._paused = False
        self._setup_ui()
        self._setup_log_listener()

    def _setup_ui(self) -> None:
        """Configura a interface do terminal."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont("Consolas", 9))
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a0a;
                color: #e0e0e0;
                border: none;
                padding: 8px;
                selection-background-color: #333366;
            }
        """)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self._text_edit)

    def _setup_log_listener(self) -> None:
        """Configura listener para receber logs."""
        self.log_received.connect(self._append_log)
        LogEmitter.add_listener(self._on_log)

    def _on_log(self, record: logging.LogRecord) -> None:
        """Callback chamado para cada log emitido."""
        entry = LogEntry(record)
        self.log_received.emit(entry)

    @Slot(object)
    def _append_log(self, entry: LogEntry) -> None:
        """Adiciona uma entrada de log ao terminal."""
        if self._paused:
            return

        timestamp = entry.timestamp.strftime("%H:%M:%S")
        level = entry.level.ljust(8)

        message = entry.message
        if message.startswith(f"[{entry.level}]"):
            message = message[len(entry.level) + 3 :].strip()

        safe_msg = _escape(message)

        html = (
            f'<span style="color: #666666;">{timestamp}</span> '
            f'<span style="color: {entry.color};">{level}</span> '
            f'<span style="color: #e0e0e0;">{safe_msg}</span><br>'
        )

        self._text_edit.insertHtml(html)

        scrollbar = self._text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        self._trim_lines()

    def _trim_lines(self) -> None:
        """Remove linhas antigas se exceder o limite."""
        doc = self._text_edit.document()
        if doc.blockCount() > self._max_lines:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(
                QTextCursor.Down,
                QTextCursor.KeepAnchor,
                doc.blockCount() - self._max_lines,
            )
            cursor.removeSelectedText()

    def clear(self) -> None:
        """Limpa o terminal."""
        self._text_edit.clear()

    def pause(self) -> None:
        """Pausa a atualizacao do terminal."""
        self._paused = True

    def resume(self) -> None:
        """Retoma a atualizacao do terminal."""
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    def set_max_lines(self, lines: int) -> None:
        """Define o numero maximo de linhas."""
        self._max_lines = max(100, lines)