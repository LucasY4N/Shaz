"""
core/use_cases/programming_assistant.py
Diagnóstico de erros, análise de logs, geração de patches e explicações técnicas.
"""
from __future__ import annotations
from dataclasses import dataclass
from core.ports.interfaces import LLMPort
from infrastructure.logging.logger import logger


@dataclass
class DiagnosticResult:
    error_type: str
    root_cause: str
    patch: str
    explanation: str
    references: list[str]


class ProgrammingAssistantUseCase:
    """Assistente especializado em diagnóstico e correção de código."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def diagnose_error(
        self,
        error_message: str,
        code_context: str | None = None,
        language: str = "python",
    ) -> DiagnosticResult:
        """Analisa um erro e gera diagnóstico + patch."""
        logger.info(f"[ProgrammingAssistant] diagnose | lang={language}")

        prompt_parts = [
            f"Analise este erro em {language}:",
            f"```\n{error_message}\n```",
        ]
        if code_context:
            prompt_parts.append(f"\nContexto do código:\n```{language}\n{code_context}\n```")

        prompt = "\n".join(prompt_parts)
        prompt += "\n\nResponda APENAS com JSON no formato:\n"
        prompt += '{"error_type":"...","root_cause":"...","patch":"...","explanation":"...","references":[]}'

        system = (
            "Você é um especialista em debugging e engenharia de software. "
            "Analise erros com precisão cirúrgica. Retorne apenas JSON válido."
        )

        raw = await self._llm.complete(
            [{"role": "user", "content": prompt}],
            system_prompt=system,
            temperature=0.2,
        )

        return self._parse_response(raw)

    async def analyze_logs(self, logs: str) -> str:
        """Analisa logs e identifica anomalias."""
        logger.info("[ProgrammingAssistant] analyze_logs")
        prompt = f"Analise estes logs e identifique erros, warnings e anomalias:\n\n```\n{logs[:4000]}\n```"
        return await self._llm.complete(
            [{"role": "user", "content": prompt}],
            system_prompt="Você é um especialista em análise de logs. Seja conciso e direto.",
            temperature=0.1,
        )

    async def explain_code(self, code: str, language: str = "python") -> str:
        """Explica um trecho de código de forma didática."""
        prompt = f"Explique este código {language} de forma clara e didática:\n\n```{language}\n{code}\n```"
        return await self._llm.complete(
            [{"role": "user", "content": prompt}],
            temperature=0.5,
        )

    def _parse_response(self, raw: str) -> DiagnosticResult:
        import json, re
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(match.group() if match else raw)
            return DiagnosticResult(**data)
        except Exception as e:
            logger.warning(f"[ProgrammingAssistant] parse error: {e}")
            return DiagnosticResult(
                error_type="unknown",
                root_cause=raw[:200],
                patch="",
                explanation=raw,
                references=[],
            )
