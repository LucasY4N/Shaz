"""
backend/routes/tools.py
Rotas para ferramentas externas: clima, pesquisa, Wikipedia, GitHub.
Delega toda a lógica para os respectivos serviços em apis/.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from backend.schemas.requests import (
    SearchRequest, GitHubRepoRequest, WeatherRequest, DiagnoseRequest,
)
from backend.schemas.responses import ActionResponse
from logs.logger import get_module_logger

log = get_module_logger(__name__)
router = APIRouter(prefix="/tools", tags=["Tools"])


def register(app_state: dict):

    @router.post("/weather", response_model=ActionResponse)
    async def get_weather(req: WeatherRequest) -> ActionResponse:
        """Retorna clima atual para uma cidade."""
        weather_svc = app_state.get("weather_service")
        if not weather_svc:
            raise HTTPException(503, detail="API de clima não configurada. Adicione OPENWEATHER_API_KEY no .env")
        try:
            weather = await weather_svc.get_current(req.city)
            return ActionResponse(status="ok", data={
                "city": weather.city,
                "country": weather.country,
                "temperature": weather.temperature,
                "feels_like": weather.feels_like,
                "humidity": weather.humidity,
                "description": weather.description,
                "wind_speed": weather.wind_speed,
                "text": weather.to_text(),
            })
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    @router.post("/search", response_model=ActionResponse)
    async def web_search(req: SearchRequest) -> ActionResponse:
        """Pesquisa na web via Tavily."""
        tavily_svc = app_state.get("tavily_service")
        if not tavily_svc:
            raise HTTPException(503, detail="Tavily não configurado. Adicione TAVILY_API_KEY no .env")
        try:
            results = await tavily_svc.search(req.query, max_results=req.max_results)
            return ActionResponse(status="ok", data={
                "query": results.query,
                "answer": results.answer,
                "context": results.to_context(),
                "results": [
                    {"title": r.title, "url": r.url, "snippet": r.snippet}
                    for r in results.results
                ],
            })
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    @router.post("/wikipedia", response_model=ActionResponse)
    async def wikipedia_lookup(req: SearchRequest) -> ActionResponse:
        """Busca informações no Wikipedia."""
        wiki_svc = app_state.get("wikipedia_service")
        if not wiki_svc:
            raise HTTPException(503, detail="Serviço Wikipedia não disponível")
        try:
            article = await wiki_svc.summary(req.query)
            return ActionResponse(status="ok", data={
                "title": article.title,
                "summary": article.summary,
                "url": article.url,
            })
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    @router.post("/github/repo", response_model=ActionResponse)
    async def analyze_repo(req: GitHubRepoRequest) -> ActionResponse:
        """Analisa um repositório GitHub."""
        github_svc = app_state.get("github_service")
        if not github_svc:
            raise HTTPException(503, detail="GitHub não configurado. Adicione GITHUB_TOKEN no .env")
        try:
            analysis = await github_svc.analyze_repo(req.owner, req.repo)
            return ActionResponse(status="ok", data=analysis)
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    @router.post("/diagnose", response_model=ActionResponse)
    async def diagnose_error(req: DiagnoseRequest) -> ActionResponse:
        """Diagnostica um erro de programação."""
        coding_agent = app_state.get("coding_agent")
        if not coding_agent:
            raise HTTPException(503, detail="Agente de código não disponível")
        try:
            result = await coding_agent.diagnose(req.error, req.code, req.language)
            return ActionResponse(status="ok", data={
                "error_type": result.error_type,
                "root_cause": result.root_cause,
                "patch": result.patch,
                "explanation": result.explanation,
                "references": result.references,
            })
        except Exception as e:
            raise HTTPException(500, detail=str(e))

    return router
