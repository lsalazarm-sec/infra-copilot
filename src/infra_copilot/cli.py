"""Command-line entrypoint."""

from __future__ import annotations

import asyncio
import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from infra_copilot import __version__
from infra_copilot.agents.main import ask
from infra_copilot.config import CONFIG_FILE, Settings

app = typer.Typer(
    name="copilot",
    help="Local LLM assistant for sysadmins and SREs.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


def _load_settings() -> Settings:
    try:
        return Settings.load()
    except Exception as e:
        err_console.print(f"[red]Failed to load config:[/red] {e}")
        sys.exit(2)


@app.command()
def version() -> None:
    """Print version and exit."""
    console.print(f"infra-copilot {__version__}")


@app.command()
def ask_cmd(
    prompt: Annotated[str, typer.Argument(help="Natural language query.")],
    model: Annotated[str | None, typer.Option("--model", "-m", help="Override LLM model.")] = None,
) -> None:
    """One-shot query against the agent."""
    settings = _load_settings()
    if model:
        settings.llm.model = model

    with console.status("[bold cyan]Thinking..."):
        answer = asyncio.run(ask(prompt, settings))

    console.print(Markdown(answer))


app.command(name="ask")(ask_cmd)


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    from infra_copilot.ui.tui import run_tui
    settings = _load_settings()
    run_tui(settings)


@app.command()
def init() -> None:
    """Write default config to ~/.config/infra-copilot/config.yaml."""
    if CONFIG_FILE.exists():
        err_console.print(f"[yellow]Config already exists at {CONFIG_FILE}[/yellow]")
        raise typer.Exit(code=1)
    Settings().save()
    console.print(f"[green]Config written to {CONFIG_FILE}[/green]")


if __name__ == "__main__":
    app()
