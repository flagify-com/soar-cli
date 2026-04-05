import pytest
from typer.testing import CliRunner
import json

from soar_client.main import app, state
from soar_client.client import SOARClient

runner = CliRunner()

@pytest.fixture
def mock_client(mocker):
    client_mock = mocker.patch("soar_client.commands.playbook.get_client")
    mock_instance = mocker.Mock(spec=SOARClient)
    client_mock.return_value = mock_instance
    return mock_instance

def test_list_playbooks_human(mock_client):
    mock_client.list_playbooks.return_value = [
        {"id": 1, "name": "pb_1", "displayName": "Test Playbook", "playbookCategory": "Security"}
    ]
    
    # Ensure json_mode is off
    state["json_mode"] = False
    
    result = runner.invoke(app, ["playbook", "list"])
    assert result.exit_code == 0
    assert "Test Playbook" in result.stdout
    assert "Security" in result.stdout

def test_list_playbooks_json(mock_client):
    mock_client.list_playbooks.return_value = [
        {"id": 1, "name": "pb_1", "displayName": "Test Playbook", "description": "Desc"}
    ]
    
    # Enable json mode directly just like the cli flag does before running command logic
    # In real usage, the callback handles it, but CliRunner might need it set explicitly if running subcommands
    result = runner.invoke(app, ["--json", "playbook", "list"])
    assert result.exit_code == 0
    
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["data"]["total"] == 1
    assert data["data"]["playbooks"][0]["displayName"] == "Test Playbook"

def test_search_playbooks(mock_client):
    mock_client.list_playbooks.return_value = [
        {"id": 1, "name": "pb_1", "displayName": "Login Failure", "description": "Handles login"}
    ]
    
    state["json_mode"] = False
    result = runner.invoke(app, ["playbook", "search", "Login"])
    assert result.exit_code == 0
    assert "Login Failure" in result.stdout

def test_execute_playbook_success(mock_client):
    mock_client.execute_playbook.return_value = "activity-12345"
    
    state["json_mode"] = False
    result = runner.invoke(app, ["playbook", "execute", "100", "--params", '{"ip": "1.1.1.1"}'])
    assert result.exit_code == 0
    assert "activity-12345" in result.stdout
    
    # Verify the client method was called properly
    mock_client.execute_playbook.assert_called_once_with(100, {"ip": "1.1.1.1"}, 0)

def test_execute_playbook_invalid_json(mock_client):
    result = runner.invoke(app, ["playbook", "execute", "100", "--params", 'invalid-json'])
    assert result.exit_code == 1
    assert "Invalid JSON" in result.stdout
