import typer
import json
from rich.table import Table
from typing import Optional

from soar_client.client import SOARClient

app = typer.Typer(no_args_is_help=True)

def get_client() -> SOARClient:
    try:
        return SOARClient()
    except ValueError as e:
        from soar_client.main import print_result
        print_result(str(e), success=False)
        raise typer.Exit(code=1)

def extract_text_from_draftjs(description: str) -> str:
    """Extracts plain text from DraftJS format (raw JSON) often found in playbooks."""
    if not description:
        return ""
    try:
        data = json.loads(description)
        if "blocks" in data and isinstance(data["blocks"], list):
            return " ".join(block.get("text", "") for block in data["blocks"])
    except (json.JSONDecodeError, TypeError):
        pass
    return description

@app.command("list")
def list_playbooks(category: Optional[str] = typer.Option(None, help="Filter by playbook category")):
    """
    List all available active playbooks.
    """
    client = get_client()
    try:
        playbooks = client.list_playbooks(category=category)
        
        from soar_client.main import state, print_result, console
        if state["json_mode"]:
            # Reduce fields
            formatted = [{"id": p.get("id"), "name": p.get("name"), "displayName": p.get("displayName"), "description": extract_text_from_draftjs(p.get("description", ""))} for p in playbooks]
            print_result({"total": len(playbooks), "playbooks": formatted})
        else:
            table = Table(title="SOAR Playbooks")
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Display Name", style="magenta")
            table.add_column("System Name", style="green")
            table.add_column("Category")

            for p in playbooks:
                table.add_row(
                    str(p.get("id", "")),
                    p.get("displayName", ""),
                    p.get("name", ""),
                    p.get("playbookCategory", "N/A")
                )
            console.print(table)
            console.print(f"Total: {len(playbooks)} playbooks")
    except Exception as e:
        from soar_client.main import print_result
        print_result(f"Failed to list playbooks: {e}", success=False)
        raise typer.Exit(code=1)

@app.command("search")
def search_playbooks(query: str = typer.Argument(..., help="Text to search in playbook name or description")):
    """
    Search playbooks by name or description.
    """
    client = get_client()
    try:
        playbooks = client.list_playbooks()
        matched = []
        for p in playbooks:
            name = (p.get("name") or "").lower()
            display = (p.get("displayName") or "").lower()
            desc = (p.get("description") or "").lower()
            q = query.lower()
            if q in name or q in display or q in desc:
                matched.append(p)

        from soar_client.main import state, print_result, console
        if state["json_mode"]:
            formatted = [{"id": p.get("id"), "name": p.get("name"), "displayName": p.get("displayName")} for p in matched]
            print_result({"total": len(matched), "playbooks": formatted})
        else:
            if not matched:
                console.print(f"No playbooks found matching '{query}'")
                return
            
            table = Table(title=f"Search Results for '{query}'")
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Display Name", style="magenta")
            table.add_column("Description")

            for p in matched:
                table.add_row(
                    str(p.get("id", "")),
                    p.get("displayName", ""),
                    extract_text_from_draftjs(p.get("description", "N/A"))
                )
            console.print(table)
    except Exception as e:
        from soar_client.main import print_result
        print_result(f"Failed to search playbooks: {e}", success=False)
        raise typer.Exit(code=1)

@app.command("params")
def playbook_params(playbook_id: int = typer.Argument(..., help="The ID of the playbook")):
    """
    Get the required parameters for a specific playbook.
    """
    client = get_client()
    try:
        params_data = client.get_playbook_params(playbook_id)
        
        from soar_client.main import state, print_result, console
        
        # Parse params similarly to how sync_service does
        parsed_params = []
        for item in params_data:
            param_configs = item.get("paramConfigs", [])
            is_required = any(config.get("required", False) for config in param_configs)
            parsed_params.append({
                "paramName": item.get("cefColumn", ""),
                "paramDesc": item.get("cefDesc", ""),
                "paramType": item.get("valueType", ""),
                "required": is_required
            })
            
        if state["json_mode"]:
            print_result({"playbookId": playbook_id, "params": parsed_params})
        else:
            if not parsed_params:
                console.print(f"[yellow]Playbook {playbook_id} has no defined parameters.[/yellow]")
                return
                
            table = Table(title=f"Parameters for Playbook {playbook_id}")
            table.add_column("Parameter Name", style="cyan")
            table.add_column("Description")
            table.add_column("Type")
            table.add_column("Required", justify="center")

            for p in parsed_params:
                req_col = "[red]Yes[/red]" if p["required"] else "No"
                table.add_row(p["paramName"], p["paramDesc"], p["paramType"], req_col)
            console.print(table)
    except Exception as e:
        from soar_client.main import print_result
        print_result(f"Failed to get playbook params: {e}", success=False)
        raise typer.Exit(code=1)

@app.command("execute")
def execute(
    playbook_id: int = typer.Argument(..., help="The ID of the playbook to run"),
    params: str = typer.Option("{}", "--params", help="JSON string representing the parameters"),
    event_id: int = typer.Option(0, "--event-id", help="Optional Event ID to bind this execution to")
):
    """
    Execute a playbook with given parameters.
    """
    client = get_client()
    try:
        try:
            param_dict = json.loads(params)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON provided for --params: {params}")
            
        activity_id = client.execute_playbook(playbook_id, param_dict, event_id)
        
        from soar_client.main import print_result, console, state
        if state["json_mode"]:
            print_result({"activity_id": activity_id, "playbook_id": playbook_id})
        else:
            console.print(f"[green]Successfully started execution for Playbook {playbook_id}[/green]")
            console.print(f"Activity ID: [bold cyan]{activity_id}[/bold cyan]")
            console.print(f"To check status: [yellow]soar-cli playbook status {activity_id}[/yellow]")
            
    except Exception as e:
        from soar_client.main import print_result
        print_result(f"Execution failed: {e}", success=False)
        raise typer.Exit(code=1)

@app.command("status")
def status(activity_id: str = typer.Argument(..., help="The Activity ID returned from execute")):
    """
    Check the status of a playbook execution.
    """
    client = get_client()
    try:
        status_data = client.get_execution_status(activity_id)
        exec_status = status_data.get('executeStatus', 'UNKNOWN')
        
        from soar_client.main import print_result, console, state
        if state["json_mode"]:
            print_result({
                "activityId": activity_id,
                "status": exec_status,
                "details": status_data
            })
        else:
            color = "green" if exec_status == "SUCCESS" else "yellow" if exec_status == "RUNNING" else "red"
            console.print(f"Execution Status: [bold {color}]{exec_status}[/bold {color}]")
            
            console.print(f"To see results: [yellow]soar-cli playbook result {activity_id}[/yellow]")
    except Exception as e:
        from soar_client.main import print_result
        print_result(f"Status check failed: {e}", success=False)
        raise typer.Exit(code=1)

@app.command("result")
def result(activity_id: str = typer.Argument(..., help="The Activity ID returned from execute")):
    """
    Fetch the detailed results of a playbook execution.
    """
    client = get_client()
    try:
        result_data = client.get_execution_result(activity_id)
        
        from soar_client.main import print_result, console, state
        if state["json_mode"]:
            print_result({"activityId": activity_id, "result": result_data})
        else:
            # We dump the raw result structure back 
            console.print("Execution Result Data:")
            console.print_json(data=result_data)
    except Exception as e:
        from soar_client.main import print_result
        print_result(f"Result fetch failed: {e}", success=False)
        raise typer.Exit(code=1)
