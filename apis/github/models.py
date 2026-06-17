"""
apis/github/models.py
Modelos de dados para respostas da API do GitHub.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GitHubRepo:
    name: str
    full_name: str
    description: str
    html_url: str
    stars: int
    forks: int
    language: str
    open_issues: int
    default_branch: str
    topics: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GitHubRepo":
        return cls(
            name=data.get("name", ""),
            full_name=data.get("full_name", ""),
            description=data.get("description") or "",
            html_url=data.get("html_url", ""),
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            language=data.get("language") or "Unknown",
            open_issues=data.get("open_issues_count", 0),
            default_branch=data.get("default_branch", "main"),
            topics=data.get("topics", []),
        )


@dataclass
class GitHubUser:
    login: str
    name: str
    bio: str
    public_repos: int
    followers: int
    following: int
    html_url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GitHubUser":
        return cls(
            login=data.get("login", ""),
            name=data.get("name") or "",
            bio=data.get("bio") or "",
            public_repos=data.get("public_repos", 0),
            followers=data.get("followers", 0),
            following=data.get("following", 0),
            html_url=data.get("html_url", ""),
        )


@dataclass
class GitHubCommit:
    sha: str
    message: str
    author: str
    date: str
    url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GitHubCommit":
        commit = data.get("commit", {})
        return cls(
            sha=data.get("sha", "")[:7],
            message=commit.get("message", "").split("\n")[0],
            author=commit.get("author", {}).get("name", ""),
            date=commit.get("author", {}).get("date", ""),
            url=data.get("html_url", ""),
        )
