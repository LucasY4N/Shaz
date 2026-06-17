"""
backend/schemas/requests.py
Schemas Pydantic para validação de requisições da API.
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)


class ProviderRequest(BaseModel):
    provider: str


class VoiceRequest(BaseModel):
    voice: str


class EngineRequest(BaseModel):
    engine: str


class PromptRequest(BaseModel):
    prompt: str = Field(..., max_length=8192)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)


class GitHubRepoRequest(BaseModel):
    owner: str
    repo: str


class WeatherRequest(BaseModel):
    city: str


class DiagnoseRequest(BaseModel):
    error: str = Field(..., min_length=1)
    code: str = ""
    language: str = "python"
