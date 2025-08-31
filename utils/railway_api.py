import os
import requests
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from utils.logger import log_error, log_info, log_warning
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

class RailwayAPI:
    """Helper class for interacting with Railway API - Log fetching removed"""
    
    def __init__(self, api_token: Optional[str] = None, max_retries: int = 3, 
                 rate_limit: int = 100):
        """Initialize with optional API token and retry settings"""
        self.api_token = api_token or os.getenv('RAILWAY_API_TOKEN')
        self.api_url = "https://backboard.railway.com/graphql/v2"
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
        
        log_info("Railway API initialized (log fetching disabled)")
        
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
    
    def get_project_info(self) -> Dict:
        """Get information about the current project"""
        try:
            query = """
            query CurrentProject {
                project {
                    id
                    name
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

    def close(self):
        """Close the requests session"""
        try:
            self.session.close()
        except:
            pass