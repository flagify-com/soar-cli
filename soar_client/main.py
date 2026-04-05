import typer
import json
from rich.console import Console

from soar_client.commands import playbook

app = typer.Typer(
    name="soar-cli",
    help="OctoMation / HoneyGuide SOAR Command Line Interface",
    epilog=(
        "由【上海雾帜智能科技有限公司】(flagify.com) 提供支持。\n"
        "开源地址: https://github.com/flagify-com/soar-cli\n"
        "兄弟项目 soar-mcp: https://github.com/flagify-com/soar-mcp\n"
        "平台核心 OctoMation: https://github.com/flagify-com/OctoMation"
    ),
    no_args_is_help=True
)

app.add_typer(playbook.app, name="playbook", help="Manage and execute SOAR playbooks")

console = Console()

# Global state to track if we should output strictly JSON
# This is extremely useful for Agent execution parsing
state = {"json_mode": False}

def version_callback(value: bool):
    if value:
        from soar_client import __version__
        typer.echo(f"soar-cli version: {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    output_json: bool = typer.Option(
        False, 
        "--json", "-j", 
        help="Enable JSON output mode for Agent parsers"
    ),
    version: bool = typer.Option(
        None,
        "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show the application's version and exit."
    )
):
    """
    SOAR CLI tool globally configured.
    Use --json to ensure stdout only prints parseable JSON output.
    """
    if output_json:
        state["json_mode"] = True

def print_result(data, success=True):
    """Unified print function that respects json_mode"""
    if state["json_mode"]:
        # In JSON mode, wrap it cleanly and disable rich formatting
        wrapped = {
            "success": success,
            "data": data
        }
        print(json.dumps(wrapped, ensure_ascii=False, indent=2))
    else:
        # In human mode, Use rich
        if success:
            console.print(data)
        else:
            console.print(f"[red]Error:[/red] {data}")

if __name__ == "__main__":
    app()
