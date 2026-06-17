"""
agents/research_agent.py
Agente de pesquisa: combina Tavily, Wikipedia e GitHub para responder perguntas.
Responsabilidade única: buscar e sintetizar informações externas.
"""
from __future__ import annotations

from logs.logger import get_module_logger

log = get_module_logger(__name__)


class ResearchAgent:
    """
    Agente que usa ferramentas externas para pesquisa.
    Combina web search, Wikipedia e GitHub conforme o contexto.
    """

    def __init__(
        self,
        llm_service,               # type: ignore[annotation]
        tavily_service=None,       # type: ignore[annotation]
        wikipedia_service=None,    # type: ignore[annotation]
        github_service=None,       # type: ignore[annotation]
    ) -> None:
        self._llm = llm_service
        self._tavily = tavily_service
        self._wiki = wikipedia_service
        self._github = github_service

    async def research(self, query: str, depth: str = "basic") -> str:
        """
        Pesquisa um tópico usando todas as fontes disponíveis.

        Args:
            query: O que pesquisar
            depth: 'basic' (rápido) ou 'advanced' (detalhado)

        Returns:
            Texto com o resultado da pesquisa
        """
        log.info(f"ResearchAgent: {query!r} (depth={depth})")
        context_parts: list[str] = []

        # Web search via Tavily
        if self._tavily:
            try:
                results = await self._tavily.search(query, max_results=5)
                context_parts.append(f"## Pesquisa Web\n{results.to_context()}")
            except Exception as e:
                log.warning(f"Tavily search failed: {e}")

        # Wikipedia (se parece ser uma consulta de conhecimento)
        if self._wiki and self._is_knowledge_query(query):
            try:
                article = await self._wiki.summary(query)
                context_parts.append(f"## Wikipedia\n{article.to_context()}")
            except Exception as e:
                log.debug(f"Wikipedia lookup failed: {e}")

        # Se não tem fontes, responde direto
        if not context_parts:
            return await self._llm.complete(
                messages=[{"role": "user", "content": query}],
                system_prompt="Você é um pesquisador. Responda com base no seu conhecimento.",
                temperature=0.5,
            )

        context = "\n\n".join(context_parts)
        prompt = (
            f"Com base nas seguintes fontes, responda: {query}\n\n"
            f"{context}\n\n"
            "Sintetize as informações de forma clara e objetiva em português."
        )

        return await self._llm.complete(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="Você é um pesquisador que sintetiza informações de múltiplas fontes.",
            temperature=0.3,
        )

    async def analyze_github_repo(self, owner: str, repo: str) -> str:
        """Analisa um repositório GitHub e gera um relatório."""
        if not self._github:
            return "Serviço GitHub não configurado. Adicione GITHUB_TOKEN no .env"

        try:
            analysis = await self._github.analyze_repo(owner, repo)
            prompt = (
                f"Analise este repositório GitHub e forneça um resumo técnico em português:\n\n"
                f"{analysis}"
            )
            return await self._llm.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
        except Exception as e:
            log.error(f"GitHub analysis failed: {e}")
            return f"Erro ao analisar repositório: {e}"

    def _is_knowledge_query(self, query: str) -> bool:
        """Heurística simples para identificar consultas de conhecimento."""
        knowledge_keywords = [
            "o que é", "quem é", "quando", "onde", "como funciona",
            "explique", "definição de", "história de", "what is", "who is",
        ]
        q = query.lower()
        return any(kw in q for kw in knowledge_keywords)
