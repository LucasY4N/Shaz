"""
agents/coding_agent.py
Agente de programação: diagnóstico de erros, geração de patches, análise de código.
Responsabilidade única: tudo que envolve código e debugging.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from logs.logger import get_module_logger

log = get_module_logger(__name__)


@dataclass
class DiagnosticResult:
    error_type: str
    root_cause: str
    patch: str
    explanation: str
    references: list[str] = field(default_factory=list)


class CodingAgent:
    """
    Agente especializado em código e debugging.
    Diagnostica erros, sugere patches e explica código.
    """

    SYSTEM_PROMPT = (
        "Você é um especialista em engenharia de software e debugging com profundo conhecimento "
        "em Python, JavaScript, TypeScript e outros. "
        "Analise com precisão cirúrgica. Seja objetivo e técnico. "
        "Quando solicitado JSON, retorne APENAS JSON válido, sem markdown."
    )

    def __init__(self, llm_service) -> None:  # type: ignore[annotation]
        self._llm = llm_service

    async def diagnose(
        self,
        error: str,
        code_context: str | None = None,
        language: str = "python",
    ) -> DiagnosticResult:
        """
        Analisa um erro e gera diagnóstico + patch.

        Args:
            error: Mensagem de erro completa
            code_context: Trecho de código onde o erro ocorreu (opcional)
            language: Linguagem de programação

        Returns:
            DiagnosticResult com causa raiz, patch e explicação
        """
        log.info(f"CodingAgent diagnosing error in {language}")

        parts = [f"Analise este erro em {language}:\n```\n{error}\n```"]
        if code_context:
            parts.append(f"\nContexto:\n```{language}\n{code_context}\n```")

        parts.append(
            '\nResponda APENAS com JSON:\n'
            '{"error_type":"...","root_cause":"...","patch":"...","explanation":"...","references":[]}'
        )

        response = await self._llm.complete(
            messages=[{"role": "user", "content": "\n".join(parts)}],
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.1,
        )
        return self._parse_diagnostic(response)

    async def explain(self, code: str, language: str = "python") -> str:
        """Explica um trecho de código de forma clara e didática."""
        prompt = f"Explique este código {language} de forma clara e didática:\n\n```{language}\n{code}\n```"
        return await self._llm.complete(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.4,
        )

    async def review(self, code: str, language: str = "python") -> str:
        """Faz code review com sugestões de melhoria."""
        prompt = (
            f"Faça code review deste código {language}. "
            "Aponte: bugs, code smells, melhorias de performance e de legibilidade.\n\n"
            f"```{language}\n{code}\n```"
        )
        return await self._llm.complete(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.2,
        )

    def _parse_diagnostic(self, raw: str) -> DiagnosticResult:
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(match.group() if match else raw)
            return DiagnosticResult(**data)
        except Exception as e:
            log.warning(f"CodingAgent parse error: {e}")
            return DiagnosticResult(
                error_type="unknown",
                root_cause=raw[:300],
                patch="",
                explanation=raw,
            )
