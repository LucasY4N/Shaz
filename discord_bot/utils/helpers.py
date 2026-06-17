"""
discord_bot/utils/helpers.py
Utilitários de formatação para respostas no Discord.
"""
from __future__ import annotations

import discord
from discord_bot.config.constants import (
    COLOR_SHAZ, COLOR_ERROR, COLOR_SUCCESS, COLOR_INFO,
    COLOR_WARNING, MAX_MSG_LENGTH, EMOJI_SHAZ,
)


def truncate(text: str, limit: int = MAX_MSG_LENGTH) -> str:
    """Trunca texto para o limite do Discord."""
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."


def shaz_embed(
    title: str,
    description: str = "",
    color: int = COLOR_SHAZ,
    footer: str = "Shaz AI • Pyxis-7",
) -> discord.Embed:
    """Cria um embed padrão da Shaz."""
    embed = discord.Embed(
        title=f"{EMOJI_SHAZ} {title}",
        description=truncate(description, 4000),
        color=color,
    )
    embed.set_footer(text=footer)
    return embed


def error_embed(message: str) -> discord.Embed:
    """Embed de erro padrão."""
    return discord.Embed(
        title="❌ Erro",
        description=message,
        color=COLOR_ERROR,
    )


def success_embed(title: str, description: str = "") -> discord.Embed:
    """Embed de sucesso padrão."""
    return discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=COLOR_SUCCESS,
    )


def weather_embed(data: dict) -> discord.Embed:
    """Embed formatado para clima."""
    d = data.get("data", {})
    embed = discord.Embed(
        title=f"🌤 Clima — {d.get('city', '?')}, {d.get('country', '?')}",
        description=d.get("description", "").capitalize(),
        color=COLOR_INFO,
    )
    embed.add_field(name="🌡 Temperatura", value=f"{d.get('temperature', '?')}°C", inline=True)
    embed.add_field(name="🤔 Sensação", value=f"{d.get('feels_like', '?')}°C", inline=True)
    embed.add_field(name="💧 Umidade", value=f"{d.get('humidity', '?')}%", inline=True)
    embed.add_field(name="💨 Vento", value=f"{d.get('wind_speed', '?')} m/s", inline=True)
    embed.set_footer(text="Shaz AI • OpenWeatherMap")
    return embed


def github_embed(data: dict) -> discord.Embed:
    """Embed formatado para análise de repositório GitHub."""
    repo = data.get("data", {}).get("repository", {})
    commits = data.get("data", {}).get("recent_commits", [])
    issues = data.get("data", {}).get("open_issues", [])

    embed = discord.Embed(
        title=f"🐙 {repo.get('name', 'Repositório')}",
        description=repo.get("description", "Sem descrição") or "Sem descrição",
        url=repo.get("url", ""),
        color=COLOR_SHAZ,
    )
    embed.add_field(name="⭐ Stars", value=str(repo.get("stars", 0)), inline=True)
    embed.add_field(name="🍴 Forks", value=str(repo.get("forks", 0)), inline=True)
    embed.add_field(name="💻 Linguagem", value=repo.get("language", "?"), inline=True)

    if commits:
        commit_lines = "\n".join(
            f"`{c['sha']}` {c['message'][:60]} — *{c['author']}*"
            for c in commits[:3]
        )
        embed.add_field(name="📝 Commits recentes", value=commit_lines, inline=False)

    if issues:
        issue_lines = "\n".join(
            f"#{i['number']} {i['title'][:60]}"
            for i in issues[:3]
        )
        embed.add_field(name="🐛 Issues abertas", value=issue_lines, inline=False)

    embed.set_footer(text="Shaz AI • GitHub")
    return embed


def diagnostic_embed(data: dict) -> discord.Embed:
    """Embed para diagnóstico de código."""
    d = data.get("data", {})
    embed = discord.Embed(
        title=f"🩺 Diagnóstico — {d.get('error_type', 'Erro desconhecido')}",
        color=COLOR_WARNING,
    )
    embed.add_field(name="🔍 Causa raiz", value=truncate(d.get("root_cause", "?"), 1024), inline=False)
    if d.get("patch"):
        embed.add_field(
            name="🔧 Patch sugerido",
            value=f"```python\n{truncate(d.get('patch', ''), 900)}\n```",
            inline=False,
        )
    embed.add_field(name="💡 Explicação", value=truncate(d.get("explanation", "?"), 1024), inline=False)
    embed.set_footer(text="Shaz AI • CodingAgent")
    return embed


def status_embed(data: dict) -> discord.Embed:
    """Embed de status do sistema."""
    embed = discord.Embed(
        title="⚡ Status do Sistema Shaz",
        color=COLOR_SUCCESS if data.get("online") else COLOR_ERROR,
    )
    embed.add_field(name="🌐 Online", value="Sim ✅" if data.get("online") else "Não ❌", inline=True)
    embed.add_field(name="🤖 Provedor", value=data.get("current_provider", "?"), inline=True)
    embed.add_field(name="💬 Mensagens", value=str(data.get("messages_session", 0)), inline=True)

    services = data.get("services", {})
    if services:
        svc_text = "\n".join(
            f"{'✅' if v == 'ok' else '⚠️' if v == 'not_configured' else '❌'} {k}"
            for k, v in services.items()
        )
        embed.add_field(name="🔌 Serviços", value=svc_text, inline=False)

    embed.set_footer(text="Shaz AI • NEXUS v3.0")
    return embed
