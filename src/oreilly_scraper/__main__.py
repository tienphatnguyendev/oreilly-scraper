import sys
from rich.console import Console
from .settings import load_config

console = Console()

def main():
    console.print("[bold green]O'Reilly PDF Downloader[/bold green] initializing...")
    try:
        config = load_config()
        console.print(f"Loaded config for book URL: {config.get('book_url')}")
    except Exception as e:
        console.print(f"[bold red]Error loading config:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
