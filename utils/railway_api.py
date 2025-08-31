import os
import requests
from typing import Dict, Optional, List
from utils.logger import log_error, log_info

class RailwayAPI:
    """Helper class for interacting with Railway API"""
    
    def __init__(self, api_token: Optional[str] = None):
        """Initialize with optional API token"""
        self.api_token = api_token or os.getenv('RAILWAY_API_TOKEN')
        self.base_url = "https://backboard.railway.app/graphql"
        
    def _make_request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Make GraphQL request to Railway API"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_token}"
            }
            
            data = {
                "query": query,
                "variables": variables or {}
            }
            
            response = requests.post(self.base_url, json=data, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            log_error(f"Railway API request failed: {str(e)}")
            return {"errors": [{"message": str(e)}]}
    
    def get_logs(self, project_id: str, service_id: str, limit: int = 100) -> List[Dict]:
        """Get logs for a service"""
        try:
            query = """
            query ServiceLogs($projectId: String!, $serviceId: String!, $limit: Int!) {
                logs(projectId: $projectId, serviceId: $serviceId, limit: $limit) {
                    timestamp
                    message
                    severity
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id,
                "limit": limit
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching logs: {result['errors']}")
                return []
                
            return result.get("data", {}).get("logs", [])
            
        except Exception as e:
            log_error(f"Failed to get logs: {str(e)}")
            return []
    
    def get_project_info(self) -> Dict:
        """Get information about the current project"""
        try:
            query = """
            query CurrentProject {
                project {
                    id
                    name
                    services {
                        id
                        name
                    }
                }
            }
            """
            
            result = self._make_request(query)
            
            if "errors" in result:
                log_error(f"Error fetching project info: {result['errors']}")
                return {}
                
            return result.get("data", {}).get("project", {})
            
        except Exception as e:
            log_error(f"Failed to get project info: {str(e)}")
            return {}
    
    def get_service_metrics(self, project_id: str, service_id: str) -> Dict:
        """Get metrics for a service"""
        try:
            query = """
            query ServiceMetrics($projectId: String!, $serviceId: String!) {
                metrics(projectId: $projectId, serviceId: $serviceId) {
                    cpu
                    memory
                    requests
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching metrics: {result['errors']}")
                return {}
                
            return result.get("data", {}).get("metrics", {})
            
        except Exception as e:
            log_error(f"Failed to get metrics: {str(e)}")
            return {}
    
    def get_deployments(self, project_id: str, service_id: str, limit: int = 10) -> List[Dict]:
        """Get recent deployments for a service"""
        try:
            query = """
            query ServiceDeployments($projectId: String!, $serviceId: String!, $limit: Int!) {
                deployments(projectId: $projectId, serviceId: $serviceId, limit: $limit) {
                    id
                    status
                    createdAt
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id,
                "limit": limit
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching deployments: {result['errors']}")
                return []
                
            return result.get("data", {}).get("deployments", [])
            
        except Exception as e:
            log_error(f"Failed to get deployments: {str(e)}")
            return []