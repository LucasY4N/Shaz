"""
main.py
Ponto de entrada principal do Shaz AI.
Interface CLI com Typer.
"""
from __future__ import annotations
import asyncio
import typer
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

app = typer.Typer(name="shaz", help="⚡ Shaz AI — Assistente inteligente hexagonal")
console = Console()

# Container global (inicializado no startup)
_container = None


async def _get_container():
    global _container
    if _container is None:
        from services.container import Container
        _container = await Container.build()
    return _container


# ─── Commands ────────────────────────────────────────────────────────────────

@app.command()
def chat(
    message: Optional[str] = typer.Argument(None, help="Mensagem para a IA"),
    conversation_id: Optional[str] = typer.Option(None, "--conv", help="ID da conversa"),
    user: str = typer.Option("default", "--user", help="ID do usuário"),
    stream: bool = typer.Option(False, "--stream", help="Resposta em streaming"),
) -> None:
    """💬 Conversar com a Shaz AI."""

    async def _run() -> None:
        c = await _get_container()
        use_message = message or Prompt.ask("[bold cyan]Você[/bold cyan]")
        response = await c.chat_use_case.chat(  # type: ignore
            user_message=use_message,
            conversation_id=conversation_id,
            user_id=user,
        )
        console.print(Panel(response, title="[bold green]Shaz[/bold green]", border_style="green"))

    asyncio.run(_run())


@app.command()
def diagnose(
    error: str = typer.Argument(..., help="Mensagem de erro para diagnosticar"),
    code: Optional[str] = typer.Option(None, "--code", help="Código contexto"),
    lang: str = typer.Option("python", "--lang", help="Linguagem"),
) -> None:
    """🔍 Diagnosticar um erro de programação."""

    async def _run() -> None:
        c = await _get_container()
        result = await c.programming_use_case.diagnose_error(  # type: ignore
            error_message=error,
            code_context=code,
            language=lang,
        )
        console.print(Panel(
            f"[bold]Tipo:[/bold] {result.error_type}\n"
            f"[bold]Causa:[/bold] {result.root_cause}\n\n"
            f"[bold]Patch:[/bold]\n```\n{result.patch}\n```\n\n"
            f"[bold]Explicação:[/bold] {result.explanation}",
            title="[red]🔍 Diagnóstico[/red]",
            border_style="red",
        ))

    asyncio.run(_run())


@app.command()
def learn(url: str = typer.Argument(..., help="URL do vídeo YouTube")) -> None:
    """📚 Aprender a partir de um vídeo do YouTube."""

    async def _run() -> None:
        c = await _get_container()
        console.print(f"[yellow]⏳ Processando vídeo: {url}[/yellow]")
        knowledge = await c.youtube_use_case.learn_from_video(url)  # type: ignore

        console.print(Panel(
            f"[bold]Resumo:[/bold]\n{knowledge.summary}\n\n"
            f"[bold]Conceitos:[/bold] {', '.join(knowledge.key_concepts)}\n\n"
            f"[bold]Perguntas:[/bold]\n" + "\n".join(f"• {q}" for q in knowledge.questions),
            title="[bold blue]📚 Conhecimento Extraído[/bold blue]",
            border_style="blue",
        ))

        if knowledge.flashcards:
            console.print("\n[bold]Flashcards:[/bold]")
            for i, card in enumerate(knowledge.flashcards, 1):
                console.print(f"  {i}. Q: {card.get('q','')}\n     A: {card.get('a','')}")

    asyncio.run(_run())


@app.command()
def dashboard(
    mongo_uri: str = typer.Option("mongodb://localhost:27017", "--mongo", help="URI MongoDB"),
) -> None:
    """📊 Abrir terminal dashboard (CPU, RAM, MongoDB, logs)."""
    from dashboard.terminal_dashboard import run_dashboard
    asyncio.run(run_dashboard(mongo_uri=mongo_uri))


@app.command()
def voice() -> None:
    """🎙️ Iniciar modo de voz (STT → IA → TTS)."""

    async def _run() -> None:
        c = await _get_container()
        console.print("[bold green]🎙️ Modo de voz ativado. Fale algo (Ctrl+C para sair).[/bold green]")
        while True:
            try:
                console.print("[dim]Ouvindo...[/dim]")
                text = await c.stt.listen()  # type: ignore
                if not text:
                    continue
                console.print(f"[cyan]Você:[/cyan] {text}")
                response = await c.chat_use_case.chat(user_message=text)  # type: ignore
                console.print(f"[green]Shaz:[/green] {response}")
                await c.tts.speak(response)  # type: ignore
            except KeyboardInterrupt:
                break

    asyncio.run(_run())


if __name__ == "__main__":
    app()
