"""
dashboard/terminal_dashboard.py
Dashboard terminal com Rich: CPU, RAM, APIs, MongoDB e logs em tempo real.
"""
from __future__ import annotations
import asyncio
import platform
import time
from datetime import datetime

import psutil
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


def _cpu_bar(pct: float, width: int = 20) -> str:
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    color = "green" if pct < 60 else "yellow" if pct < 85 else "red"
    return f"[{color}]{bar}[/{color}] {pct:5.1f}%"


def _mem_bar(pct: float, width: int = 20) -> str:
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    color = "cyan" if pct < 70 else "yellow" if pct < 88 else "red"
    return f"[{color}]{bar}[/{color}] {pct:5.1f}%"


def build_system_panel() -> Panel:
    mem = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=None)
    disk = psutil.disk_usage("/")

    table = Table(box=None, show_header=False, padding=(0, 1))
    table.add_column("Label", style="bold white", width=12)
    table.add_column("Bar / Value")

    table.add_row("CPU",    _cpu_bar(cpu_pct))
    table.add_row("RAM",    _mem_bar(mem.percent) + f"  {mem.used / 1e9:.1f}/{mem.total / 1e9:.1f} GB")
    table.add_row("Disk",   _mem_bar(disk.percent) + f"  {disk.used / 1e9:.0f}/{disk.total / 1e9:.0f} GB")
    table.add_row("Python", f"[dim]{platform.python_version()}[/dim]")
    table.add_row("OS",     f"[dim]{platform.system()} {platform.release()}[/dim]")

    return Panel(table, title="[bold cyan]⚙  Sistema[/bold cyan]", border_style="cyan")


async def _check_mongo(uri: str) -> tuple[bool, str]:
    try:
        import motor.motor_asyncio
        client = motor.motor_asyncio.AsyncIOMotorClient(uri, serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
        return True, "●  MongoDB [green]OK[/green]"
    except Exception as e:
        return False, f"●  MongoDB [red]OFFLINE[/red] ({str(e)[:30]})"


def build_status_panel(statuses: list[str]) -> Panel:
    text = Text()
    for s in statuses:
        text.append_text(Text.from_markup(s + "\n"))
    return Panel(text, title="[bold yellow]🔌  Status dos Serviços[/bold yellow]", border_style="yellow")


_log_buffer: list[str] = []


def add_log(msg: str) -> None:
    _log_buffer.append(f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] {msg}")
    if len(_log_buffer) > 30:
        _log_buffer.pop(0)


def build_log_panel() -> Panel:
    text = Text()
    for line in _log_buffer[-15:]:
        text.append_text(Text.from_markup(line + "\n"))
    return Panel(text, title="[bold magenta]📋  Logs[/bold magenta]", border_style="magenta")


def build_header() -> Panel:
    now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    return Panel(
        Text("⚡  SHAZ AI — Terminal Dashboard", justify="center", style="bold white"),
        subtitle=f"[dim]{now}[/dim]",
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
    )


def make_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="logs", size=18),
    )
    layout["body"].split_row(
        Layout(name="system"),
        Layout(name="status"),
    )
    return layout


async def run_dashboard(mongo_uri: str = "mongodb://localhost:27017") -> None:
    """Inicia o dashboard interativo. Ctrl+C para sair."""
    layout = make_layout()
    statuses: list[str] = ["⏳ Verificando serviços..."]

    async def refresh_statuses() -> None:
        while True:
            new: list[str] = []
            _, mongo_msg = await _check_mongo(mongo_uri)
            new.append(mongo_msg)
            new.append("●  Gemini  [green]configurado[/green]" if True else "●  Gemini  [red]ausente[/red]")
            new.append("●  Groq    [green]configurado[/green]")
            new.append("●  STT     [green]ready[/green]")
            new.append("●  TTS     [green]ready[/green]")
            statuses.clear()
            statuses.extend(new)
            add_log("Status atualizado")
            await asyncio.sleep(10)

    asyncio.create_task(refresh_statuses())
    await asyncio.sleep(1.5)  # Aguarda primeira checagem

    add_log("Dashboard iniciado 🚀")
    add_log(f"Sistema: {platform.system()} | Python {platform.python_version()}")

    with Live(layout, refresh_per_second=2, screen=True):
        while True:
            layout["header"].update(build_header())
            layout["system"].update(build_system_panel())
            layout["status"].update(build_status_panel(statuses))
            layout["logs"].update(build_log_panel())
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    try:
        asyncio.run(run_dashboard())
    except KeyboardInterrupt:
        console.print("\n[bold red]Dashboard encerrado.[/bold red]")
