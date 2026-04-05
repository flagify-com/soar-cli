import os
import httpx
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from urllib.parse import urljoin

# Load environment variables
load_dotenv()

class SOARClient:
    def __init__(self):
        self.base_url = os.environ.get("SOAR_BASE_URL", "http://127.0.0.1:8080")
        self.token = os.environ.get("SOAR_API_TOKEN", "")
        self.verify_ssl = os.environ.get("SOAR_VERIFY_SSL", "False").lower() in ("true", "1", "yes")
        
        if not self.token:
            raise ValueError("SOAR_API_TOKEN environment variable is not set. Please check your .env file.")

        self.headers = {
            "hg-token": self.token,
            "Content-Type": "application/json"
        }
        
    def _check_response(self, response: httpx.Response, entity_name: str = "Resource"):
        if response.status_code >= 400:
            msg = response.text
            try:
                err_data = response.json()
                msg = err_data.get("message") or err_data.get("msg") or msg
            except Exception:
                pass
            
            if response.status_code == 404:
                raise Exception(f"{entity_name} 不存在 (404 Not Found)。详细信息: {msg}")
            elif response.status_code == 400:
                raise Exception(f"请求参数错误 (400 Bad Request)。详细信息: {msg}")
            else:
                raise Exception(f"API 请求失败 ({response.status_code}): {msg}")

    def _get_client(self) -> httpx.Client:
        # Use a synchronous client for simplicity in the CLI, unless async is heavily required
        # For agent CLIs, synchronous execution is perfectly fine and often preferred for simple scripts.
        return httpx.Client(
            headers=self.headers,
            verify=self.verify_ssl,
            timeout=30.0
        )

    def list_playbooks(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        # This endpoint requires publishStatus ONLINE based on the soar-mcp code
        url = f"{self.base_url.rstrip('/')}/odp/core/v1/api/playbook/findAll"
        payload = {"publishStatus": "ONLINE"}
        
        with self._get_client() as client:
            response = client.post(url, json=payload)
            self._check_response(response, "Playbook List")
            data = response.json()
            
            if data.get("code") != 200:
                raise Exception(f"API Error: {data.get('message')}")
                
            playbooks = data.get("result", [])
            if category:
                playbooks = [p for p in playbooks if p.get("playbookCategory") == category]
                
            return playbooks

    def get_playbook_params(self, playbook_id: int) -> List[Dict[str, Any]]:
        url = f"{self.base_url.rstrip('/')}/api/playbook/param?playbookId={playbook_id}"
        with self._get_client() as client:
            response = client.post(url)
            self._check_response(response, "Playbook")
            data = response.json()
            
            if data.get("code") != 200:
                raise Exception(f"API Error: {data.get('message')}")
                
            return data.get("result", [])

    def execute_playbook(self, playbook_id: int, parameters: Dict[str, str], event_id: int = 0) -> str:
        url = f"{self.base_url.rstrip('/')}/api/event/execution"
        api_params = [{"key": key, "value": str(value)} for key, value in parameters.items()]
        
        payload = {
            "eventId": event_id,
            "executorInstanceId": playbook_id,
            "executorInstanceType": "PLAYBOOK",
            "params": api_params
        }
        
        with self._get_client() as client:
            response = client.post(url, json=payload)
            self._check_response(response, "Playbook (Execute)")
            data = response.json()
            
            if data.get("code") != 200:
                raise Exception(f"API Error: {data.get('message')}")
                
            activity_id = data.get("result")
            if not activity_id:
                raise Exception("API did not return an activity_id")
                
            return activity_id

    def get_execution_status(self, activity_id: str) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/odp/core/v1/api/activity/{activity_id}"
        
        with self._get_client() as client:
            response = client.get(url)
            self._check_response(response, "Activity")
            data = response.json()
            
            if data.get("code") != 200:
                raise Exception(f"API Error: {data.get('message')}")
                
            return data.get("result", {})

    def get_execution_result(self, activity_id: str) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/odp/core/v1/api/event/activity?activityId={activity_id}"
        
        with self._get_client() as client:
            response = client.get(url)
            self._check_response(response, "Activity Result")
            data = response.json()
            
            if data.get("code") != 200:
                raise Exception(f"API Error: {data.get('message')}")
                
            return data.get("result", {})
