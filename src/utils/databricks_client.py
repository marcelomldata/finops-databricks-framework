import os
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class DatabricksConfig:
    host: str
    token: str
    workspace_id: Optional[str] = None

class DatabricksAPIClient:
    def __init__(self, config: DatabricksConfig):
        self.host = config.host.rstrip('/')
        self.token = config.token
        self.workspace_id = config.workspace_id
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        url = f"{self.host}/api/2.0/{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def get_clusters(self) -> List[Dict]:
        return self._request("GET", "clusters/list").get("clusters", [])
    
    def get_cluster_details(self, cluster_id: str) -> Dict:
        return self._request("GET", f"clusters/get?cluster_id={cluster_id}")
    
    def get_jobs(self) -> List[Dict]:
        return self._request("GET", "jobs/list").get("jobs", [])
    
    def get_job_runs(self, job_id: Optional[int] = None, limit: int = 1000) -> List[Dict]:
        endpoint = "jobs/runs/list"
        params = {"limit": limit}
        if job_id:
            params["job_id"] = job_id
        return self._request("GET", endpoint, params=params).get("runs", [])
    
    def get_job_details(self, job_id: int) -> Dict:
        return self._request("GET", f"jobs/get?job_id={job_id}")
    
    def get_sql_warehouses(self) -> List[Dict]:
        return self._request("GET", "sql/warehouses/list").get("warehouses", [])
    
    def get_workspace_info(self) -> Dict:
        return self._request("GET", "workspace/list", params={"path": "/"})
