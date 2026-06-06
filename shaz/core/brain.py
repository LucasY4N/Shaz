"""
shaz/core/brain.py
Cérebro principal do Shaz AI - Orquestrador central.
Coordena: LLM, Memória, Personalidade, Voz (STT/TTS), Áudio e UI.
Gerencia o fluxo completo de conversação.
"""
from __future__ import annotations

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from shaz.core.config import Config
from shaz.core.memory import Memory
from shaz.core.personality import Personality
from shaz.services.api_manager import APIManager, LLMResponse
from shaz.voice.stt import FasterWhisperSTT, STTFactory
from shaz.voice.tts import TTSManager, TTSFactory
from shaz.voice.audio import AudioManager, AudioPlayer
from shaz.utils.helpers import get_system_info
from shaz.utils.logger import logger


class ShazBrain:
    """
    Cérebro central da Shaz AI.
    Coordena todos os módulos e gerencia o fluxo de conversação.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        memory: Optional[Memory] = None,
        personality: Optional[Personality] = None,
        api_manager: Optional[APIManager] = None,
        stt: Optional[FasterWhisperSTT] = None,
        tts: Optional[TTSManager] = None,
        audio: Optional[AudioManager] = None,
    ) -> None:
        self._config = config or Config()
        self._memory = memory or Memory(self._config.memory_db_path)
        self._personality = personality or Personality(self._memory)
        self._api = api_manager or APIManager(self._config)
        self._stt = stt or STTFactory.create(self._config)
        self._tts = tts or TTSFactory.create(self._config)
        self._audio = audio or AudioManager(self._config)

        self._user_id = "default"
        self._conversation_id: Optional[str] = None
        self._is_running = False
        self._voice_mode = False
        self._on_status_change: Optional[Callable[[str], None]] = None
        self._on_response: Optional[Callable[[str], None]] = None

        # Sistema de fila de fala (inicializado preguiçosamente para evitar erro de loop)
        self._speak_queue: Optional[asyncio.Queue[str]] = None
        self._speak_worker_task: Optional[asyncio.Task] = None

        # Carrega usuário
        self._user = self._memory.get_or_create_user(self._user_id)
        logger.system(f"ShazBrain initialized | user={self._user_id}")

    async def process_message(self, text: str) -> str:
        """
        Processa uma mensagem do usuário e retorna a resposta.

        Fluxo:
        1. Salva mensagem na memória
        2. Busca contexto (histórico + memórias)
        3. Monta system prompt com personalidade
        4. Chama LLM
        5. Salva resposta na memória
        6. Atualiza memórias relevantes
        7. Retorna resposta

        Args:
            text: Mensagem do usuário

        Returns:
            Resposta da Shaz
        """
        if not text or not text.strip():
            return "..."

        logger.info(f"Processing message: {text[:60]}...")
        self._notify_status("processing")

        try:
            # 1. Salva mensagem do usuário
            msg_id, self._conversation_id = self._memory.save_message(
                role="user",
                content=text,
                user_id=self._user_id,
                conversation_id=self._conversation_id,
            )

            # 2. Busca contexto
            history = self._memory.get_conversation_context(
                self._user_id, max_messages=self._config.max_history_per_conversation
            )

            memories_text = self._memory.get_memory_context(text, self._user_id)

            # 3. Monta contexto extra
            extra_context = f"Data/hora atual: {datetime.now().strftime('%d/%m/%Y %H:%M')}"

            # 4. Monta system prompt
            system_prompt = self._personality.build_system_prompt(
                language=self._config.language,
                extra_context=extra_context,
                memories=memories_text,
            )

            # 5. Prepara mensagens para o LLM
            messages = self._personality.build_conversation_context(history)

            # Adiciona a mensagem atual
            messages.append({"role": "user", "content": text})

            # 6. Chama LLM
            response: LLMResponse = await self._api.complete(
                messages=messages,
                system_prompt=system_prompt,
            )

            answer = response.content
            if not answer:
                answer = "Desculpe, não consegui processar sua solicitação."

            # 7. Salva resposta
            self._memory.save_message(
                role="assistant",
                content=answer,
                user_id=self._user_id,
                conversation_id=self._conversation_id,
            )

            # 8. Extrai memórias importantes heuristicamente
            await self._extract_memories(text, answer)

            # 9. Notifica resposta
            self._notify_response(answer)

            # 10. Atualiza timestamps
            self._memory.update_user_seen(self._user_id)

            logger.info(f"Response generated ({len(answer)} chars)")
            self._notify_status("online")
            return answer

        except Exception as e:
            logger.error(f"Brain error processing message: {e}")
            self._notify_status("online")
            return f"Desculpe, ocorreu um erro ao processar sua mensagem: {str(e)}"

    async def _extract_memories(self, user_msg: str, response: str) -> None:
        """Extrai e salva memórias importantes da conversa."""
        triggers = [
            "meu nome", "eu gosto", "eu prefiro", "minha cor", "eu odeio",
            "moro em", "eu trabalho", "meu aniversario", "nasci em",
            "eu estudo", "meu time", "minha serie", "meu filme",
        ]

        if any(t in user_msg.lower() for t in triggers):
            self._memory.save_memory(
                content=f"Usuario disse: {user_msg[:200]}",
                memory_type="preference",
                user_id=self._user_id,
                importance=0.7,
            )
            logger.memory("Preference memory saved from conversation")

        # Salva interação
        self._memory.save_memory(
            content=f"Interacao: User='{user_msg[:100]}' -> Shaz='{response[:100]}'",
            memory_type="interaction",
            user_id=self._user_id,
            importance=0.3,
        )

    async def process_voice(self) -> None:
        """
        Modo de voz completo: ouve -> transcreve -> processa -> fala.
        Loop contínuo.
        """
        if not self._stt.is_available:
            logger.error("[Voice] STT not available. Cannot start voice mode.")
            return

        self._voice_mode = True
        logger.voice("Voice mode activated")

        self._notify_status("listening")

        while self._voice_mode:
            try:
                # 1. Grava áudio
                self._notify_status("listening")
                audio_bytes = self._audio.recorder.record_speech(
                    timeout=10.0,
                    phrase_limit=15.0,
                )

                if not audio_bytes:
                    continue

                # 2. Transcreve
                self._notify_status("processing")
                text = self._stt.transcribe_bytes(audio_bytes)

                if not text:
                    logger.stt("No speech detected")
                    continue

                logger.stt(f"Transcribed: {text}")

                # 3. Processa
                response = await self.process_message(text)

                if not response:
                    continue

                # 4. Fala
                self._notify_status("speaking")
                # Adiciona à fila e espera terminar antes de ouvir de novo (evita eco)
                await self.speak(response, wait=True)

            except Exception as e:
                logger.error(f"[Voice] Error in voice loop: {e}")
                await asyncio.sleep(0.5)

        self._notify_status("online")
        logger.voice("Voice mode deactivated")

    def stop_voice_mode(self) -> None:
        """Para o modo de voz."""
        self._voice_mode = False
        self._audio.player.stop()
        self._audio.recorder.stop_recording()
        # Limpa a fila de fala pendente se houver
        if self._speak_queue:
            while not self._speak_queue.empty():
                try: self._speak_queue.get_nowait()
                except: pass
        logger.voice("Voice mode deactivated by user")

    def _ensure_speak_worker(self) -> None:
        """Garante que a fila e o worker de fala estejam inicializados e rodando."""
        if self._speak_queue is None:
            self._speak_queue = asyncio.Queue()
        if self._speak_worker_task is None or self._speak_worker_task.done():
            self._speak_worker_task = asyncio.create_task(self._speak_worker())

    async def speak(self, text: str, wait: bool = False) -> None:
        """
        Adiciona um texto à fila de fala da Shaz.
        
        Args:
            text: Texto para falar
            wait: Se True, aguarda a conclusão da fala antes de retornar
        """
        if not text:
            return
        
        self._ensure_speak_worker()
        await self._speak_queue.put(text)
        if wait:
            await self._speak_queue.join()

    async def _speak_worker(self) -> None:
        """Trabalhador em segundo plano que processa a fila de fala sequencialmente."""
        if self._speak_queue is None:
            return
        while True:
            text = await self._speak_queue.get()
            try:
                self._notify_status("speaking")
                audio = await self._tts.synthesize(text)
                if audio:
                    # Executa o player síncrono em uma thread para não travar o loop principal
                    await asyncio.to_thread(self._audio.player.play_bytes, audio)
            except Exception as e:
                logger.error(f"[Brain] Speak worker error: {e}")
            finally:
                self._notify_status("online")
                self._speak_queue.task_done()

    def get_conversation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtém o histórico recente de conversas."""
        return self._memory.get_recent_messages(self._user_id, limit)

    def get_memories(self, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtém memórias salvas."""
        return self._memory.get_all_memories(self._user_id, memory_type)

    def get_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do sistema."""
        stats = self._memory.stats()
        stats["providers"] = self._api.available_providers
        stats["current_provider"] = self._api.current_provider
        stats["tts_engines"] = self._tts.available_engines
        stats["voice_active"] = self._voice_mode
        return stats

    def set_provider(self, provider: str) -> bool:
        """Troca o provedor LLM."""
        return self._api.set_provider(provider)

    def clear_history(self) -> None:
        """Limpa o histórico de conversas."""
        count = self._memory.clear_conversation_history(self._user_id)
        self._conversation_id = None
        logger.memory(f"Conversation history cleared ({count} messages)")

    def set_on_status_change(self, callback: Callable[[str], None]) -> None:
        """Callback para mudanças de status."""
        self._on_status_change = callback

    def set_on_response(self, callback: Callable[[str], None]) -> None:
        """Callback para quando uma resposta é gerada."""
        self._on_response = callback

    def _notify_status(self, status: str) -> None:
        """Notifica listeners sobre mudança de status."""
        if self._on_status_change:
            try:
                self._on_status_change(status)
            except Exception:
                pass

    def _notify_response(self, response: str) -> None:
        """Notifica listeners sobre resposta gerada."""
        if self._on_response:
            try:
                self._on_response(response)
            except Exception:
                pass

    @property
    def is_voice_active(self) -> bool:
        return self._voice_mode

    @property
    def memory(self) -> Memory:
        return self._memory

    @property
    def personality(self) -> Personality:
        return self._personality

    @property
    def api(self) -> APIManager:
        return self._api

    @property
    def config(self) -> Config:
        return self._config


# ─── Factory ──────────────────────────────────────────────────────────────

def create_brain(
    config: Optional[Config] = None,
    memory: Optional[Memory] = None,
) -> ShazBrain:
    """Factory function para criar o cérebro Shaz."""
    return ShazBrain(config=config, memory=memory)


__all__ = ["ShazBrain", "create_brain"]