"""
shaz/ui/chat.py
Widget de chat para o Shaz AI.
Interface de conversação com histórico, entrada de texto e modo de voz.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class ChatBubble:
    """Representa uma bolha de mensagem no chat."""

    def __init__(self, role: str, content: str, timestamp: Optional[str] = None) -> None:
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")

    def to_html(self) -> str:
        """Converte a mensagem para HTML."""
        if self.role == "user":
            return (
                f'<div style="margin: 8px 0; text-align: right;">'
                f'<div style="display: inline-block; background: #1a3a5c; color: #e0e0e0; '
                f'border-radius: 12px 12px 4px 12px; padding: 10px 14px; '
                f'max-width: 80%; text-align: left;">'
                f'<div style="font-size: 11px; color: #5a8fbb; margin-bottom: 4px;">Você</div>'
                f'{self._escape(self.content)}'
                f'<div style="font-size: 10px; color: #888; margin-top: 4px; text-align: right;">'
                f'{self.timestamp}</div></div></div>'
            )
        else:
            return (
                f'<div style="margin: 8px 0; text-align: left;">'
                f'<div style="display: inline-block; background: #1a2a1a; color: #e0e0e0; '
                f'border-radius: 12px 12px 12px 4px; padding: 10px 14px; '
                f'max-width: 80%; text-align: left;">'
                f'<div style="font-size: 11px; color: #5abb5a; margin-bottom: 4px;">Shaz</div>'
                f'{self._escape(self.content)}'
                f'<div style="font-size: 10px; color: #888; margin-top: 4px;">'
                f'{self.timestamp}</div></div></div>'
            )

    @staticmethod
    def _escape(text: str) -> str:
        """Escapa HTML e converte quebras de linha."""
        text = text.replace("&", "&").replace("<", "<").replace(">", ">")
        text = text.replace("\n", "<br>")
        # Formata código inline
        text = text.replace("`", "")
        return text


class ChatWidget(QWidget):
    """
    Widget de chat para conversar com a Shaz.
    Inclui histórico, entrada de texto e botao de envio.
    """

    message_sent = Signal(str)
    voice_activated = Signal()
    voice_deactivated = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._messages: List[ChatBubble] = []
        self._is_voice_active = False
        self._on_send_message: Optional[Callable[[str], Any]] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface do chat."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = QLabel("Conversa com Shaz")
        header.setStyleSheet("""
            QLabel {
                color: #00ff7f;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 12px;
                background: #0d1117;
                border-bottom: 1px solid #1a1a2e;
            }
        """)
        layout.addWidget(header)

        # Area de mensagens
        self._messages_area = QTextBrowser()
        self._messages_area.setReadOnly(True)
        self._messages_area.setOpenExternalLinks(False)
        self._messages_area.setStyleSheet("""
            QTextBrowser {
                background-color: #0d1117;
                color: #e0e0e0;
                border: none;
                padding: 8px;
                selection-background-color: #333366;
            }
        """)
        self._messages_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self._messages_area)

        # Area de entrada
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("Digite sua mensagem...")
        self._input_field.setStyleSheet("""
            QLineEdit {
                background-color: #161b22;
                color: #e0e0e0;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                selection-background-color: #333366;
            }
            QLineEdit:focus {
                border-color: #00ff7f;
            }
        """)
        self._input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self._input_field)

        # Botao de envio
        self._send_button = QPushButton("Enviar")
        self._send_button.setStyleSheet("""
            QPushButton {
                background-color: #00ff7f;
                color: #0d1117;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00cc66;
            }
            QPushButton:pressed {
                background-color: #00994d;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #666;
            }
        """)
        self._send_button.clicked.connect(self._send_message)
        input_layout.addWidget(self._send_button)

        # Botao de voz
        self._voice_button = QPushButton("🎤")
        self._voice_button.setStyleSheet("""
            QPushButton {
                background-color: #1a3a5c;
                color: #e0e0e0;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #2a4a6c;
            }
            QPushButton:checked {
                background-color: #ff4444;
            }
        """)
        self._voice_button.setCheckable(True)
        self._voice_button.toggled.connect(self._on_voice_toggle)
        input_layout.addWidget(self._voice_button)

        layout.addLayout(input_layout)

        # Mensagem inicial
        self.add_message("assistant", "Ola! Eu sou a Shaz. Como posso ajudar voce hoje?")

    def _send_message(self) -> None:
        """Envia a mensagem digitada."""
        text = self._input_field.text().strip()
        if not text:
            return

        self._input_field.clear()
        self.add_message("user", text)
        self.message_sent.emit(text)

        if self._on_send_message:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._async_process(text))
                else:
                    result = self._on_send_message(text)
                    if hasattr(result, "__await__"):
                        asyncio.run(self._wrap_callback(text))
                    elif isinstance(result, str):
                        self.add_message("assistant", result)
            except Exception:
                result = self._on_send_message(text)
                if isinstance(result, str):
                    self.add_message("assistant", result)

    async def _async_process(self, text: str) -> None:
        """Processa mensagem de forma assincrona."""
        if self._on_send_message:
            result = await self._on_send_message(text)
            if isinstance(result, str):
                self.add_message("assistant", result)

    async def _wrap_callback(self, text: str) -> None:
        """Wrapper para callback assincrono."""
        if self._on_send_message:
            result = await self._on_send_message(text)
            if isinstance(result, str):
                self.add_message("assistant", result)

    def _on_voice_toggle(self, checked: bool) -> None:
        """Ativa/desativa modo de voz."""
        self._is_voice_active = checked
        if checked:
            self._voice_button.setText("🔴")
            self._voice_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff4444;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-size: 16px;
                }
            """)
            self.voice_activated.emit()
        else:
            self._voice_button.setText("🎤")
            self._voice_button.setStyleSheet("""
                QPushButton {
                    background-color: #1a3a5c;
                    color: #e0e0e0;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #2a4a6c;
                }
            """)
            self.voice_deactivated.emit()

    def add_message(self, role: str, content: str) -> None:
        """Adiciona uma mensagem ao chat."""
        bubble = ChatBubble(role, content)
        self._messages.append(bubble)
        self._messages_area.append(bubble.to_html())

        scrollbar = self._messages_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_on_send(self, callback: Callable[[str], Any]) -> None:
        """Define o callback para quando uma mensagem for enviada."""
        self._on_send_message = callback

    def clear(self) -> None:
        """Limpa o chat."""
        self._messages.clear()
        self._messages_area.clear()
        self.add_message("assistant", "Chat reiniciado. Como posso ajudar?")

    @property
    def is_voice_active(self) -> bool:
        return self._is_voice_active