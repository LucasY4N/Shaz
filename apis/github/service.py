"""
apis/github/service.py
Lógica de negócio para integração com GitHub.
Analisa repositórios, commits, issues, PRs e usuários.
"""
from __future__ import annotations

from apis.github.client import GitHubClient
from apis.github.models import GitHubCommit, GitHubRepo, GitHubUser
from logs.logger import get_module_logger

log = get_module_logger(__name__)


class GitHubService:
    """Serviço de alto nível para dados do GitHub."""

    def __init__(self, token: str = "") -> None:
        self._client = GitHubClient(token)

    async def get_repo(self, owner: str, repo: str) -> GitHubRepo:
        """Retorna informações de um repositório."""
        data = await self._client.get(f"/repos/{owner}/{repo}")
        log.info(f"Fetched repo: {owner}/{repo}")
        return GitHubRepo.from_dict(data)

    async def get_user(self, username: str) -> GitHubUser:
        """Retorna informações de um usuário."""
        data = await self._client.get(f"/users/{username}")
        log.info(f"Fetched user: {username}")
        return GitHubUser.from_dict(data)

    async def get_commits(
        self,
        owner: str,
        repo: str,
        limit: int = 10,
    ) -> list[GitHubCommit]:
        """Retorna os commits mais recentes de um repositório."""
        data = await self._client.get(
            f"/repos/{owner}/{repo}/commits",
            params={"per_page": limit},
        )
        return [GitHubCommit.from_dict(c) for c in data]

    async def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10,
    ) -> list[dict]:
        """Retorna issues de um repositório."""
        data = await self._client.get(
            f"/repos/{owner}/{repo}/issues",
            params={"state": state, "per_page": limit},
        )
        return [
            {
                "number": i.get("number"),
                "title": i.get("title", ""),
                "state": i.get("state", ""),
                "url": i.get("html_url", ""),
                "labels": [lb.get("name") for lb in i.get("labels", [])],
            }
            for i in data
            if "pull_request" not in i  # Exclui PRs da lista de issues
        ]

    async def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10,
    ) -> list[dict]:
        """Retorna pull requests de um repositório."""
        data = await self._client.get(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": state, "per_page": limit},
        )
        return [
            {
                "number": pr.get("number"),
                "title": pr.get("title", ""),
                "state": pr.get("state", ""),
                "author": pr.get("user", {}).get("login", ""),
                "url": pr.get("html_url", ""),
                "draft": pr.get("draft", False),
            }
            for pr in data
        ]

    async def analyze_repo(self, owner: str, repo: str) -> dict:
        """
        Análise completa de um repositório: info + commits recentes + issues abertas.
        Retorna tudo consolidado em um dicionário para uso pelo agente de pesquisa.
        """
        repo_info = await self.get_repo(owner, repo)
        commits = await self.get_commits(owner, repo, limit=5)
        issues = await self.get_issues(owner, repo, limit=5)

        return {
            "repository": {
                "name": repo_info.full_name,
                "description": repo_info.description,
                "url": repo_info.html_url,
                "language": repo_info.language,
                "stars": repo_info.stars,
                "forks": repo_info.forks,
                "open_issues": repo_info.open_issues,
                "topics": repo_info.topics,
            },
            "recent_commits": [
                {
                    "sha": c.sha,
                    "message": c.message,
                    "author": c.author,
                    "date": c.date,
                }
                for c in commits
            ],
            "open_issues": issues,
        }

    async def close(self) -> None:
        await self._client.close()
