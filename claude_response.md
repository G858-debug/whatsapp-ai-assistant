<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0330 -->
<!-- Tokens: ~11,002 -->

## ANALYSIS
To enable viewing Railway logs, we need to add a module to interact with the Railway API. This will involve creating a new utility module for Railway API interactions.

## FILES TO CHANGE

### NEW FILE: utils/railway_api.py
```python
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
```

### UPDATE FILE: requirements.txt
```python
# Core Framework
Flask==2.3.3
python-dotenv==1.0.0

# WhatsApp & Communication
requests==2.31.0
twilio==8.9.0

# Database
supabase==1.2.0

# AI & NLP
anthropic==0.7.0

# Scheduling
APScheduler==3.10.4

# Utilities
pytz==2023.3
python-dateutil==2.8.2

# Logging & Monitoring
colorlog==6.7.0

# Payment Processing
# Note: PayFast doesn't have an official Python SDK
# Using requests for API calls

# Data Processing
pandas==2.2.0
numpy==1.26.4

# Security
cryptography==41.0.4

# Analytics
user-agents==2.2.0

# Voice Processing
pydub==0.25.1
# speech_recognition==3.10.0  # Optional, not currently used

# Testing (dev only)
pytest==7.4.2
pytest-cov==4.1.0

# Production Server
gunicorn==21.2.0

# Railway Integration
requests==2.31.0  # Already included above
```

## SUMMARY
1. Created new `utils/railway_api.py` module to interact with Railway's API
2. Added required dependencies to requirements.txt
3. Implemented key Railway API methods:
   - Get service logs
   - Get project info  
   - Get service metrics
   - Get deployment info
4. Added error handling and logging
5. Used Railway's GraphQL API for all interactions

The RailwayAPI class can now be used to:
- View application logs
- Monitor service metrics
- Track deployments
- Get project/service information

To use this, you'll need to:
1. Get a Railway API token
2. Set it as RAILWAY_API_TOKEN environment variable 
3. Initialize RailwayAPI class and call desired methods

This provides programmatic access to Railway logs and metrics for monitoring the application.