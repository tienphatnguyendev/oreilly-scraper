import asyncio
import sys
from rich.console import Console
from .settings import load_config, Settings
from .browser import create_authenticated_page

console = Console()


def main():
    console.print("[bold green]O'Reilly PDF Downloader[/bold green] initializing...")
    try:
        config: Settings = load_config()
        console.print(f"Loaded config for: [cyan]{config.book_url}[/cyan]")
        console.print(f"Cookies: [yellow]{len(config.cookies)} loaded[/yellow]")
        console.print(f"Output dir: [blue]{config.output_dir}[/blue]")
    except FileNotFoundError as e:
        console.print(f"[bold red]Config not found:[/bold red] {e}")
        sys.exit(1)

    asyncio.run(_run(config))


async def _run(config: Settings):
    page = await create_authenticated_page(config)
    console.print(f"[bold green]Ready![/bold green] Authenticated at [cyan]{page.url}[/cyan]")

if __name__ == "__main__":
    main()
