"""
Railway API Integration for fetching deployment logs
"""

import os
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
from utils.logger import log_error, log_info

class RailwayAPI:
    """Handle Railway API interactions for log fetching"""
    
    def __init__(self):
        self.api_token = os.environ.get('RAILWAY_API_TOKEN')
        self.project_id = os.environ.get('RAILWAY_PROJECT_ID')
        self.service_id = os.environ.get('RAILWAY_SERVICE_ID')
        self.api_endpoint = 'https://backboard.railway.app/graphql/v2'
        
    def is_configured(self) -> bool:
        """Check if Railway API is properly configured"""
        return all([self.api_token, self.project_id, self.service_id])
    
    def fetch_railway_logs(self, limit: int = 100) -> Dict:
        """
        Fetch the last N log lines from Railway deployment
        Returns: Dict with success status and logs or error
        """
        if not self.is_configured():
            log_info("Railway API not configured - skipping log fetch")
            return {
                'success': False,
                'error': 'Railway API credentials not configured',
                'logs': []
            }
        
        try:
            # GraphQL query for fetching deployment logs
            query = """
            query GetDeploymentLogs($projectId: String!, $serviceId: String!, $limit: Int!) {
                deployments(
                    first: 1
                    input: {
                        projectId: $projectId
                        serviceId: $serviceId
                    }
                ) {
                    edges {
                        node {
                            id
                            status
                            createdAt
                            staticUrl
                            logs(last: $limit) {
                                edges {
                                    node {
                                        message
                                        timestamp
                                        severity
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """
            
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            variables = {
                'projectId': self.project_id,
                'serviceId': self.service_id,
                'limit': limit
            }
            
            payload = {
                'query': query,
                'variables': variables
            }
            
            log_info(f"Fetching last {limit} Railway logs...")
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse the logs from the GraphQL response
                logs = self._parse_railway_logs(data)
                
                log_info(f"Successfully fetched {len(logs)} log entries from Railway")
                return {
                    'success': True,
                    'logs': logs,
                    'deployment_status': self._get_deployment_status(data)
                }
            else:
                error_msg = f"Railway API returned status {response.status_code}"
                log_error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'logs': []
                }
                
        except requests.exceptions.Timeout:
            error_msg = "Railway API request timed out"
            log_error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'logs': []
            }
        except requests.exceptions.ConnectionError:
            error_msg = "Could not connect to Railway API"
            log_error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'logs': []
            }
        except Exception as e:
            error_msg = f"Error fetching Railway logs: {str(e)}"
            log_error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'logs': []
            }
    
    def _parse_railway_logs(self, graphql_response: Dict) -> List[Dict]:
        """Parse logs from Railway GraphQL response"""
        logs = []
        
        try:
            # Navigate through the GraphQL response structure
            if 'data' in graphql_response:
                deployments = graphql_response.get('data', {}).get('deployments', {})
                edges = deployments.get('edges', [])
                
                if edges and len(edges) > 0:
                    deployment = edges[0].get('node', {})
                    log_edges = deployment.get('logs', {}).get('edges', [])
                    
                    for edge in log_edges:
                        log_node = edge.get('node', {})
                        
                        # Parse timestamp
                        timestamp_str = log_node.get('timestamp', '')
                        formatted_timestamp = self._format_timestamp(timestamp_str)
                        
                        logs.append({
                            'timestamp': formatted_timestamp,
                            'message': log_node.get('message', ''),
                            'severity': log_node.get('severity', 'INFO')
                        })
            
            # If response has errors, log them
            if 'errors' in graphql_response:
                for error in graphql_response['errors']:
                    log_error(f"Railway GraphQL error: {error.get('message', 'Unknown error')}")
                    
        except Exception as e:
            log_error(f"Error parsing Railway logs: {str(e)}")
        
        return logs
    
    def _format_timestamp(self, timestamp_str: str) -> str:
        """Format Railway timestamp to readable format"""
        try:
            if timestamp_str:
                # Parse ISO format timestamp
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # Format to readable string
                return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            return timestamp_str
        except:
            return timestamp_str
    
    def _get_deployment_status(self, graphql_response: Dict) -> Optional[str]:
        """Extract deployment status from response"""
        try:
            if 'data' in graphql_response:
                deployments = graphql_response.get('data', {}).get('deployments', {})
                edges = deployments.get('edges', [])
                
                if edges and len(edges) > 0:
                    deployment = edges[0].get('node', {})
                    return deployment.get('status', 'UNKNOWN')
        except:
            pass
        
        return None
    
    def format_logs_for_context(self, logs: List[Dict], max_lines: int = 50) -> str:
        """Format logs for inclusion in GitHub comment context"""
        if not logs:
            return "No Railway logs available."
        
        # Limit the number of logs to include
        logs_to_show = logs[-max_lines:] if len(logs) > max_lines else logs
        
        formatted_lines = []
        formatted_lines.append("=== RECENT RAILWAY DEPLOYMENT LOGS ===")
        formatted_lines.append(f"(Showing last {len(logs_to_show)} of {len(logs)} log entries)")
        formatted_lines.append("")
        
        for log in logs_to_show:
            severity_emoji = {
                'ERROR': '❌',
                'WARN': '⚠️',
                'INFO': 'ℹ️',
                'DEBUG': '🔍'
            }.get(log.get('severity', 'INFO'), 'ℹ️')
            
            line = f"{severity_emoji} [{log['timestamp']}] {log['message']}"
            formatted_lines.append(line)
        
        formatted_lines.append("")
        formatted_lines.append("=== END OF RAILWAY LOGS ===")
        
        return '\n'.join(formatted_lines)
    
    def should_fetch_logs(self, task_description: str) -> bool:
        """Determine if Railway logs should be fetched based on task description"""
        # Keywords that trigger log fetching
        trigger_keywords = [
            'error', 'bug', 'crash', 'debug', 'logs', 'deployment', 
            'railway', 'not working', 'broken', 'failed', 'failure',
            'issue', 'problem', 'fix', 'investigate', 'trace', 'stack',
            '500', '502', '503', 'timeout', 'exception'
        ]
        
        task_lower = task_description.lower()
        return any(keyword in task_lower for keyword in trigger_keywords)


# Global instance
_railway_api = None

def get_railway_api() -> RailwayAPI:
    """Get or create Railway API instance"""
    global _railway_api
    if _railway_api is None:
        _railway_api = RailwayAPI()
    return _railway_api

def fetch_railway_logs(limit: int = 100) -> Dict:
    """Convenience function to fetch Railway logs"""
    api = get_railway_api()
    return api.fetch_railway_logs(limit)

def should_fetch_logs(task_description: str) -> bool:
    """Check if logs should be fetched for this task"""
    api = get_railway_api()
    return api.should_fetch_logs(task_description)

def format_logs_for_context(logs: List[Dict], max_lines: int = 50) -> str:
    """Format logs for GitHub context"""
    api = get_railway_api()
    return api.format_logs_for_context(logs, max_lines)
