import os
import requests
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from utils.logger import log_error, log_info, log_warning
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

class RailwayAPI:
    """Helper class for interacting with Railway API"""
    
    def __init__(self, api_token: Optional[str] = None, max_retries: int = 3, 
                 rate_limit: int = 100):
        """Initialize with optional API token and retry settings"""
        self.api_token = api_token or os.getenv('RAILWAY_API_TOKEN')
        self.api_url = "https://api.railway.app/graphql/v2"
        self.rate_limit = rate_limit
        self.request_count = 0
        self.last_reset = datetime.now()
        
        # Setup session with retries
        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)
        
    def _check_rate_limit(self):
        """Check and enforce rate limits"""
        now = datetime.now()
        if (now - self.last_reset).total_seconds() > 3600:
            self.request_count = 0
            self.last_reset = now
            
        if self.request_count >= self.rate_limit:
            wait_time = 3600 - (now - self.last_reset).total_seconds()
            if wait_time > 0:
                log_warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                self.request_count = 0
                self.last_reset = datetime.now()
                
        self.request_count += 1
        
    def _make_request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Make GraphQL request to Railway API with retries"""
        try:
            self._check_rate_limit()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_token}"
            }
            
            data = {
                "query": query,
                "variables": variables or {}
            }
            
            start_time = time.time()
            response = self.session.post(self.api_url, json=data, headers=headers)
            elapsed = time.time() - start_time
            
            log_info(f"Railway API request completed in {elapsed:.2f}s")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            log_error(f"Railway API request failed: {str(e)}", exc_info=True)
            return {"errors": [{"message": str(e)}]}
        except Exception as e:
            log_error(f"Unexpected error in Railway API request: {str(e)}", exc_info=True)
            return {"errors": [{"message": "Internal error"}]}

    def get_logs(self, project_id: str, service_id: str, limit: int = 100, 
                 start_time: Optional[datetime] = None, severity: Optional[str] = None) -> List[Dict]:
        """Get logs for a service with optional filtering"""
        try:
            query = """
            query ServiceLogs($projectId: String!, $serviceId: String!, $limit: Int!, 
                           $startTime: String, $severity: String) {
                logs(projectId: $projectId, serviceId: $serviceId, limit: $limit, 
                     startTime: $startTime, severity: $severity) {
                    timestamp
                    message
                    severity
                    source
                    metadata
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id,
                "limit": limit,
                "startTime": start_time.isoformat() if start_time else None,
                "severity": severity
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching logs: {result['errors']}")
                return []
                
            return result.get("data", {}).get("logs", [])
            
        except Exception as e:
            log_error(f"Failed to get logs: {str(e)}")
            return []

    def get_recent_logs(self, project_id: str, service_id: str, hours: int = 24) -> List[Dict]:
        """Get logs from last N hours"""
        start_time = datetime.now() - timedelta(hours=hours)
        return self.get_logs(project_id, service_id, limit=1000, start_time=start_time)

    def get_error_logs(self, project_id: str, service_id: str, hours: int = 24) -> List[Dict]:
        """Get error logs from last N hours"""
        start_time = datetime.now() - timedelta(hours=hours)
        return self.get_logs(project_id, service_id, limit=1000, 
                           start_time=start_time, severity="error")
    
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
                        createdAt
                        updatedAt
                    }
                    environments {
                        id
                        name
                        serviceStatuses
                    }
                    teamId
                    createdAt
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
        """Get detailed service metrics"""
        try:
            query = """
            query ServiceMetrics($projectId: String!, $serviceId: String!, $duration: String!) {
                metrics(projectId: $projectId, serviceId: $serviceId, duration: $duration) {
                    cpu {
                        usage
                        limit
                        utilization
                    }
                    memory {
                        usage
                        limit
                        utilization
                    }
                    requests {
                        total
                        success
                        failed
                        latency
                    }
                    network {
                        bytesIn
                        bytesOut
                    }
                    latency {
                        p50
                        p95
                        p99
                    }
                    uptime
                    lastRestart
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
                    completedAt
                    creator
                    commit {
                        hash
                        message
                        author
                        timestamp
                    }
                    logs {
                        message
                        timestamp
                        severity
                    }
                    rollback
                    trigger
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
        """Get detailed health status for a service"""
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
                        lastFailure
                        consecutiveSuccesses
                        consecutiveFailures
                    }
                    metrics {
                        cpu
                        memory
                        restarts
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
                    updatedAt
                    source
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

    def close(self):
        """Close the requests session"""
        try:
            self.session.close()
        except:
            pass
