<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0371 -->
<!-- Tokens: ~12,365 -->

## ANALYSIS
The Railway API utility needs to be updated to include additional monitoring functionality and better error handling. The main issues to address are:
- Add service health check functionality
- Improve error handling and logging
- Add environment variable management
- Add deployment status monitoring

## FILES TO CHANGE

### FILE: utils/railway_api.py
```python
import os
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
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
            
        except requests.exceptions.RequestException as e:
            log_error(f"Railway API request failed: {str(e)}")
            return {"errors": [{"message": str(e)}]}
        except Exception as e:
            log_error(f"Unexpected error in Railway API request: {str(e)}")
            return {"errors": [{"message": "Internal error"}]}
    
    def get_logs(self, project_id: str, service_id: str, limit: int = 100, 
                 start_time: Optional[datetime] = None) -> List[Dict]:
        """Get logs for a service with optional time filtering"""
        try:
            query = """
            query ServiceLogs($projectId: String!, $serviceId: String!, $limit: Int!, $startTime: String) {
                logs(projectId: $projectId, serviceId: $serviceId, limit: $limit, startTime: $startTime) {
                    timestamp
                    message
                    severity
                    source
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id,
                "limit": limit,
                "startTime": start_time.isoformat() if start_time else None
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
                        status
                        healthcheckUrl
                        domain
                    }
                    environments {
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
    
    def get_service_metrics(self, project_id: str, service_id: str, 
                          duration: str = "1h") -> Dict:
        """Get detailed metrics for a service"""
        try:
            query = """
            query ServiceMetrics($projectId: String!, $serviceId: String!, $duration: String!) {
                metrics(projectId: $projectId, serviceId: $serviceId, duration: $duration) {
                    cpu {
                        usage
                        limit
                    }
                    memory {
                        usage
                        limit
                    }
                    requests {
                        total
                        success
                        failed
                    }
                    latency {
                        p50
                        p95
                        p99
                    }
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id,
                "duration": duration
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
                    creator
                    commit {
                        hash
                        message
                    }
                    logs {
                        message
                        timestamp
                    }
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

    def get_service_health(self, project_id: str, service_id: str) -> Dict:
        """Get health status for a service"""
        try:
            query = """
            query ServiceHealth($projectId: String!, $serviceId: String!) {
                service(projectId: $projectId, id: $serviceId) {
                    id
                    name
                    status
                    healthcheck {
                        status
                        lastCheck
                        uptime
                    }
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching service health: {result['errors']}")
                return {}
                
            return result.get("data", {}).get("service", {})
            
        except Exception as e:
            log_error(f"Failed to get service health: {str(e)}")
            return {}

    def get_environment_variables(self, project_id: str, service_id: str) -> Dict:
        """Get environment variables for a service"""
        try:
            query = """
            query ServiceEnvVars($projectId: String!, $serviceId: String!) {
                variables(projectId: $projectId, serviceId: $serviceId) {
                    name
                    value
                    isSecret
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching environment variables: {result['errors']}")
                return {}
                
            # Filter out sensitive data from logs
            env_vars = result.get("data", {}).get("variables", [])
            for var in env_vars:
                if var.get("isSecret"):
                    var["value"] = "******"
            
            return env_vars
            
        except Exception as e:
            log_error(f"Failed to get environment variables: {str(e)}")
            return {}
```

## SUMMARY
The Railway API utility has been enhanced with:
1. Added service health check functionality
2. Added environment variable management
3. Improved error handling with specific exception types
4. Added timestamp filtering for logs
5. Enhanced metrics with detailed CPU, memory, and latency data
6. Added deployment status monitoring with commit info
7. Added secure handling of sensitive environment variables
8. Improved type hints and documentation
9. Better error logging with more context

The changes make the utility more robust and provide better monitoring capabilities for the Refiloe WhatsApp service.