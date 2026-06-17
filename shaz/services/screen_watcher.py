"""
shaz/services/screen_watcher.py

Módulo de monitoramento de tela da Shaz AI.

Fluxo:
  1. Tira um print da tela do usuário
  2. Envia a imagem para o Gemini Vision (gemini-2.5-flash)
  3. Gemini descreve o que está vendo com a personalidade da Shaz
  4. A resposta é falada em voz alta via TTS
  5. Repete após um intervalo configurável

Dependências:
  pip install pillow mss
"""
from __future__ import annotations

import asyncio
import base64
import io
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from shaz.utils.logger import logger

# ── Dependências opcionais ────────────────────────────────────────────────

try:
    import mss
    import mss.tools
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    logger.warning("[ScreenWatcher] 'mss' não instalado: pip install mss")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("[ScreenWatcher] 'Pillow' não instalado: pip install pillow")


# ── Prompt de personalidade ───────────────────────────────────────────────

SCREEN_PROMPT = """Você é a Shaz, uma IA de outro planeta (Pyxis-7) que está observando a tela do seu usuário.

Você acabou de ver uma captura de tela. Reaja a ela com a sua personalidade única:
- Seja engraçada, curiosa e um pouco tímida
- Comente o que está acontecendo na tela de forma criativa
- Se for um jogo, comente sobre o jogo
- Se for código, faça um comentário técnico com um toque de humor
- Se for um vídeo ou streaming, comente sobre o conteúdo
- Se for redes sociais, faça uma observação bem-humorada
- Se for trabalho/documentos, dê uma forcinha motivacional ou zoação carinhosa
- Se a tela estiver vazia ou travada, faça uma piada sobre isso
- Use o nome do usuário se souber, senão chame de "você" ou "Sha..." (de ShazY, apelido carinhoso)
- Mantenha a resposta CURTA: máximo 2 frases. É para ser falado em voz alta.
- Fale SEMPRE em português brasileiro
- Nunca repita a mesma frase duas vezes seguidas
- Seja espontânea, não robotizada

Exemplos do tom esperado:
- "Opa, Minecraft! Quer que eu ajude na decoração ou vai destruir mais uma casa bonita?"
- "Hmm, código Python às 2 da manhã... Isso ou é genialidade ou é desespero total."
- "YouTube de novo? Deixa eu adivinhar, caiu numa rabbit hole de vídeos aleatórios?"
- "Tela preta... ou você foi hacker agora ou travou o PC de novo."
"""


# ── Dataclasses ───────────────────────────────────────────────────────────

@dataclass
class ScreenObservation:
    """Resultado de uma observação da tela."""
    timestamp: float
    comment: str
    screenshot_bytes: bytes
    monitor_index: int = 0


# ── ScreenWatcher ─────────────────────────────────────────────────────────

class ScreenWatcher:
    """
    Monitora a tela do usuário e reage com comentários em voz da Shaz.

    Uso básico:
        watcher = ScreenWatcher(brain=brain)
        await watcher.start()   # começa o loop
        await watcher.stop()    # para o loop
    """

    def __init__(
        self,
        brain,                                        # ShazBrain
        interval_seconds: float = 30.0,               # quanto tempo entre cada observação
        monitor_index: int = 0,                        # 0 = todos os monitores, 1 = monitor principal
        resize_width: int = 1280,                      # redimensiona para economizar tokens
        on_comment: Optional[Callable[[str], None]] = None,  # callback quando gerar comentário
        speak: bool = True,                            # fala em voz alta
        save_screenshots: bool = False,                # salva prints em disco (debug)
    ) -> None:
        self._brain = brain
        self._interval = interval_seconds
        self._monitor_index = monitor_index
        self._resize_width = resize_width
        self._on_comment = on_comment
        self._speak = speak
        self._save_screenshots = save_screenshots

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_comment: str = ""
        self._observation_count: int = 0

        # Pasta para salvar screenshots (se habilitado)
        self._screenshots_dir = Path("data/screenshots")
        if self._save_screenshots:
            self._screenshots_dir.mkdir(parents=True, exist_ok=True)

        logger.system(
            f"[ScreenWatcher] Inicializado | "
            f"intervalo={interval_seconds}s | monitor={monitor_index} | "
            f"fala={speak}"
        )

    # ── API pública ───────────────────────────────────────────────────────

    async def start(self) -> None:
        """Inicia o loop de monitoramento em background."""
        if self._running:
            logger.warning("[ScreenWatcher] Já está rodando.")
            return

        if not MSS_AVAILABLE:
            raise RuntimeError("Instale o mss: pip install mss")
        if not PIL_AVAILABLE:
            raise RuntimeError("Instale o Pillow: pip install pillow")

        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.system("[ScreenWatcher] 👁 Monitoramento de tela ATIVADO")

    async def stop(self) -> None:
        """Para o loop de monitoramento."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.system("[ScreenWatcher] Monitoramento de tela DESATIVADO")

    async def observe_once(self) -> Optional[ScreenObservation]:
        """Faz uma única observação da tela (útil para testes ou chamada manual)."""
        screenshot = await self._take_screenshot()
        if screenshot is None:
            return None

        comment = await self._analyze_screenshot(screenshot)
        if not comment:
            return None

        obs = ScreenObservation(
            timestamp=time.time(),
            comment=comment,
            screenshot_bytes=screenshot,
            monitor_index=self._monitor_index,
        )

        await self._deliver(obs)
        return obs

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def observation_count(self) -> int:
        return self._observation_count

    def set_interval(self, seconds: float) -> None:
        """Altera o intervalo entre observações em tempo real."""
        self._interval = max(5.0, seconds)
        logger.system(f"[ScreenWatcher] Intervalo alterado para {self._interval}s")

    # ── Loop interno ──────────────────────────────────────────────────────

    async def _watch_loop(self) -> None:
        """Loop principal de monitoramento."""
        logger.system(f"[ScreenWatcher] Loop iniciado (intervalo={self._interval}s)")

        # Primeira observação com um pequeno delay inicial
        await asyncio.sleep(3.0)

        while self._running:
            try:
                await self.observe_once()
            except Exception as e:
                logger.error(f"[ScreenWatcher] Erro na observação: {e}")

            # Aguarda o próximo ciclo
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break

    # ── Screenshot ────────────────────────────────────────────────────────

    async def _take_screenshot(self) -> Optional[bytes]:
        """Captura a tela e retorna como bytes JPEG."""
        try:
            screenshot_bytes = await asyncio.to_thread(self._capture_sync)
            return screenshot_bytes
        except Exception as e:
            logger.error(f"[ScreenWatcher] Falha ao capturar tela: {e}")
            return None

    def _capture_sync(self) -> bytes:
        """Captura síncrona — roda em thread separada."""
        with mss.mss() as sct:
            # monitor 0 = todos; monitor 1 = principal
            monitor = sct.monitors[self._monitor_index] if self._monitor_index < len(sct.monitors) else sct.monitors[0]
            raw = sct.grab(monitor)

            # Converte para PIL Image
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

            # Redimensiona para economizar tokens (mantém aspect ratio)
            if img.width > self._resize_width:
                ratio = self._resize_width / img.width
                new_h = int(img.height * ratio)
                img = img.resize((self._resize_width, new_h), Image.LANCZOS)

            # Converte para JPEG em memória
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return buf.getvalue()

    # ── Análise com Gemini Vision ─────────────────────────────────────────

    async def _analyze_screenshot(self, image_bytes: bytes) -> Optional[str]:
        """Envia a imagem para o Gemini e obtém o comentário da Shaz."""
        try:
            # Tenta usar Gemini direto (mais eficiente para visão)
            comment = await self._analyze_with_gemini(image_bytes)
            if comment:
                return comment

            # Fallback: usa o brain (pode não ter suporte a visão)
            logger.warning("[ScreenWatcher] Gemini Vision falhou, sem fallback disponível.")
            return None

        except Exception as e:
            logger.error(f"[ScreenWatcher] Erro na análise: {e}")
            return None

    async def _analyze_with_gemini(self, image_bytes: bytes) -> Optional[str]:
        """Usa google.genai diretamente para análise de imagem."""
        try:
            import google.genai as genai
            from google.genai import types

            # Pega a API key do config do brain
            api_key = ""
            if hasattr(self._brain, "_config"):
                api_key = self._brain._config.gemini_api_key
            if not api_key:
                import os
                api_key = os.getenv("GEMINI_API_KEY", "")

            if not api_key:
                logger.error("[ScreenWatcher] GEMINI_API_KEY não encontrada")
                return None

            client = genai.Client(api_key=api_key)

            # Monta a mensagem com a imagem
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg",
            )

            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            image_part,
                            types.Part(text=SCREEN_PROMPT),
                        ],
                    )
                ],
            )

            comment = response.text.strip() if response.text else None

            # Evita repetir o mesmo comentário
            if comment and comment == self._last_comment:
                comment = None

            return comment

        except Exception as e:
            logger.error(f"[ScreenWatcher] Gemini Vision error: {e}")
            return None

    # ── Entrega do comentário ─────────────────────────────────────────────

    async def _deliver(self, obs: ScreenObservation) -> None:
        """Entrega o comentário: fala em voz + callback + log."""
        self._last_comment = obs.comment
        self._observation_count += 1

        logger.voice(f"[ScreenWatcher] 👁 Observação #{self._observation_count}: {obs.comment[:80]}")

        # Callback (para a UI mostrar o comentário no chat)
        if self._on_comment:
            try:
                self._on_comment(obs.comment)
            except Exception as e:
                logger.error(f"[ScreenWatcher] Callback error: {e}")

        # Fala em voz alta
        if self._speak and hasattr(self._brain, "speak"):
            try:
                await self._brain.speak(obs.comment)
            except Exception as e:
                logger.error(f"[ScreenWatcher] TTS error: {e}")

        # Salva screenshot (debug)
        if self._save_screenshots:
            try:
                ts = int(obs.timestamp)
                path = self._screenshots_dir / f"obs_{ts}.jpg"
                path.write_bytes(obs.screenshot_bytes)
                logger.debug(f"[ScreenWatcher] Screenshot salvo: {path}")
            except Exception as e:
                logger.debug(f"[ScreenWatcher] Falha ao salvar screenshot: {e}")
