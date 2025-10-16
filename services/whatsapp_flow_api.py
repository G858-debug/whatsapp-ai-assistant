#!/usr/bin/env python3
"""
Enhanced WhatsApp Flow API Manager
Provides comprehensive WhatsApp Flow management with advanced error handling and monitoring

⚠️  DEPRECATED: This file contains flow creation methods that should no longer be used.
    Flows should be manually created in Facebook Console instead of dynamically in code.
    This file is kept for reference and legacy script compatibility only.
"""

import json
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import log_info, log_error, log_warning
from config import Config

class WhatsAppFlowAPI:
    """Enhanced WhatsApp Flow API management"""
    
    def __init__(self):
        self.access_token = Config.WHATSAPP_ACCESS_TOKEN
        self.business_account_id = Config.WHATSAPP_BUSINESS_ACCOUNT_ID
        self.base_url = Config.BASE_URL
        self.api_version = "v18.0"
        self.base_api_url = f"https://graph.facebook.com/{self.api_version}"
        
        # Validate configuration
        self._validate_configuration()
    
    def _validate_configuration(self) -> bool:
        """Validate WhatsApp API configuration"""
        errors = []
        
        if not self.access_token:
            errors.append("WHATSAPP_ACCESS_TOKEN not configured")
        
        if not self.business_account_id:
            errors.append("WHATSAPP_BUSINESS_ACCOUNT_ID not configured")
        
        if not self.base_url:
            errors.append("BASE_URL not configured")
        
        if errors:
            log_error(f"WhatsApp Flow API configuration errors: {', '.join(errors)}")
            return False
        
        log_info("WhatsApp Flow API configuration validated successfully")
        return True
    
    def test_api_connectivity(self) -> Dict:
        """Test WhatsApp API connectivity and permissions"""
        try:
            # Test basic API access
            url = f"{self.base_api_url}/me"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Test business account access
                business_test = self._test_business_account_access()
                
                return {
                    'success': True,
                    'api_access': True,
                    'user_id': user_data.get('id'),
                    'business_account_access': business_test.get('success', False),
                    'flow_permissions': business_test.get('flow_access', False),
                    'message': 'API connectivity test successful'
                }
            else:
                return {
                    'success': False,
                    'api_access': False,
                    'error': f'API access failed: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            log_error(f"Error testing API connectivity: {str(e)}")
            return {
                'success': False,
                'api_access': False,
                'error': str(e)
            }
    
    def _test_business_account_access(self) -> Dict:
        """Test business account and flow access"""
        try:
            url = f"{self.base_api_url}/{self.business_account_id}/flows"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                flows_data = response.json()
                flows = flows_data.get('data', [])
                
                return {
                    'success': True,
                    'flow_access': True,
                    'existing_flows': len(flows),
                    'flows': flows
                }
            else:
                return {
                    'success': False,
                    'flow_access': False,
                    'error': f'Business account access failed: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'flow_access': False,
                'error': str(e)
            }
    
    def list_flows(self) -> Dict:
        """List all flows for the business account"""
        try:
            url = f"{self.base_api_url}/{self.business_account_id}/flows"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                flows_data = response.json()
                flows = flows_data.get('data', [])
                
                # Enrich flow data with additional details
                enriched_flows = []
                for flow in flows:
                    flow_details = self.get_flow_details(flow.get('id'))
                    if flow_details.get('success'):
                        enriched_flows.append(flow_details['flow_data'])
                    else:
                        enriched_flows.append(flow)
                
                return {
                    'success': True,
                    'flows': enriched_flows,
                    'total_flows': len(flows),
                    'message': f'Retrieved {len(flows)} flows successfully'
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to list flows: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            log_error(f"Error listing flows: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_flow_details(self, flow_id: str) -> Dict:
        """Get detailed information about a specific flow"""
        try:
            url = f"{self.base_api_url}/{flow_id}"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                flow_data = response.json()
                
                return {
                    'success': True,
                    'flow_data': flow_data,
                    'flow_id': flow_id,
                    'name': flow_data.get('name'),
                    'status': flow_data.get('status'),
                    'categories': flow_data.get('categories', [])
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to get flow details: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            log_error(f"Error getting flow details for {flow_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_flow(self, flow_name: str, categories: List[str] = None, endpoint_uri: str = None) -> Dict:
        """Create a new WhatsApp Flow"""
        try:
            if not categories:
                categories = ["LEAD_GENERATION", "SIGN_UP"]  # Use valid categories
            
            if not endpoint_uri:
                endpoint_uri = f"{self.base_url}/flow/webhook/flow"
            
            url = f"{self.base_api_url}/{self.business_account_id}/flows"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "name": flow_name,
                "categories": categories,
                "endpoint_uri": endpoint_uri
            }
            
            log_info(f"Creating WhatsApp Flow: {flow_name}")
            log_info(f"Categories: {categories}")
            log_info(f"Endpoint: {endpoint_uri}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                flow_id = result.get('id')
                
                log_info(f"Flow created successfully with ID: {flow_id}")
                
                return {
                    'success': True,
                    'flow_id': flow_id,
                    'flow_name': flow_name,
                    'status': 'DRAFT',
                    'message': f'Flow "{flow_name}" created successfully'
                }
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_message = error_data.get('error', {}).get('message', response.text)
                
                log_error(f"Flow creation failed: {response.status_code} - {error_message}")
                
                return {
                    'success': False,
                    'error': f'Flow creation failed: {error_message}',
                    'status_code': response.status_code,
                    'fallback_recommended': True
                }
                
        except Exception as e:
            log_error(f"Error creating flow: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fallback_recommended': True
            }
    
    def upload_flow_json(self, flow_id: str, flow_json: Dict) -> Dict:
        """Upload flow JSON to an existing flow"""
        try:
            url = f"{self.base_api_url}/{flow_id}/assets"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare the flow JSON asset
            payload = {
                "name": "flow.json",
                "asset_type": "FLOW_JSON",
                "flow_json": json.dumps(flow_json)
            }
            
            log_info(f"Uploading flow JSON to flow {flow_id}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                log_info(f"Flow JSON uploaded successfully to flow {flow_id}")
                
                return {
                    'success': True,
                    'flow_id': flow_id,
                    'message': 'Flow JSON uploaded successfully'
                }
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_message = error_data.get('error', {}).get('message', response.text)
                
                log_error(f"Flow JSON upload failed: {response.status_code} - {error_message}")
                
                return {
                    'success': False,
                    'error': f'Flow JSON upload failed: {error_message}',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            log_error(f"Error uploading flow JSON: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def publish_flow(self, flow_id: str) -> Dict:
        """Publish a flow to make it active"""
        try:
            url = f"{self.base_api_url}/{flow_id}/publish"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            log_info(f"Publishing flow {flow_id}")
            
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                log_info(f"Flow {flow_id} published successfully")
                
                # Verify the flow status
                flow_details = self.get_flow_details(flow_id)
                status = flow_details.get('flow_data', {}).get('status', 'UNKNOWN') if flow_details.get('success') else 'UNKNOWN'
                
                return {
                    'success': True,
                    'flow_id': flow_id,
                    'status': status,
                    'message': f'Flow published successfully (Status: {status})'
                }
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_message = error_data.get('error', {}).get('message', response.text)
                
                # Check for specific error types
                if 'endpoint' in error_message.lower() or 'health check' in error_message.lower():
                    return {
                        'success': False,
                        'error': 'Flow publishing requires endpoint verification and health check',
                        'error_type': 'endpoint_verification_required',
                        'recommendation': 'Verify webhook endpoint is accessible and implements health check',
                        'status_code': response.status_code
                    }
                elif 'already published' in error_message.lower():
                    return {
                        'success': True,
                        'flow_id': flow_id,
                        'status': 'PUBLISHED',
                        'message': 'Flow is already published'
                    }
                else:
                    log_error(f"Flow publishing failed: {response.status_code} - {error_message}")
                    
                    return {
                        'success': False,
                        'error': f'Flow publishing failed: {error_message}',
                        'status_code': response.status_code
                    }
                
        except Exception as e:
            log_error(f"Error publishing flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_flow(self, flow_id: str) -> Dict:
        """Delete a flow"""
        try:
            url = f"{self.base_api_url}/{flow_id}"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            log_info(f"Deleting flow {flow_id}")
            
            response = requests.delete(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                log_info(f"Flow {flow_id} deleted successfully")
                
                return {
                    'success': True,
                    'flow_id': flow_id,
                    'message': 'Flow deleted successfully'
                }
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_message = error_data.get('error', {}).get('message', response.text)
                
                log_error(f"Flow deletion failed: {response.status_code} - {error_message}")
                
                return {
                    'success': False,
                    'error': f'Flow deletion failed: {error_message}',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            log_error(f"Error deleting flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_complete_flow(self, flow_name: str, flow_json: Dict, categories: List[str] = None) -> Dict:
        """Create a complete flow with JSON and attempt to publish"""
        try:
            log_info(f"Creating complete flow: {flow_name}")
            
            # Step 1: Create the flow
            create_result = self.create_flow(flow_name, categories)
            
            if not create_result.get('success'):
                return create_result
            
            flow_id = create_result.get('flow_id')
            
            # Step 2: Upload flow JSON
            upload_result = self.upload_flow_json(flow_id, flow_json)
            
            if not upload_result.get('success'):
                # Clean up - delete the created flow
                self.delete_flow(flow_id)
                return {
                    'success': False,
                    'error': f'Flow JSON upload failed: {upload_result.get("error")}',
                    'cleanup_performed': True
                }
            
            # Step 3: Attempt to publish (optional - may fail due to endpoint verification)
            publish_result = self.publish_flow(flow_id)
            
            if publish_result.get('success'):
                return {
                    'success': True,
                    'flow_id': flow_id,
                    'flow_name': flow_name,
                    'status': 'PUBLISHED',
                    'message': f'Flow "{flow_name}" created, uploaded, and published successfully',
                    'ready_for_use': True
                }
            else:
                # Flow created and uploaded but not published
                error_type = publish_result.get('error_type')
                
                if error_type == 'endpoint_verification_required':
                    return {
                        'success': True,
                        'flow_id': flow_id,
                        'flow_name': flow_name,
                        'status': 'DRAFT',
                        'message': f'Flow "{flow_name}" created and uploaded successfully',
                        'ready_for_use': False,
                        'publish_error': publish_result.get('error'),
                        'recommendation': publish_result.get('recommendation'),
                        'next_steps': [
                            'Verify webhook endpoint is accessible',
                            'Implement health check endpoint',
                            'Retry flow publishing'
                        ]
                    }
                else:
                    return {
                        'success': True,
                        'flow_id': flow_id,
                        'flow_name': flow_name,
                        'status': 'DRAFT',
                        'message': f'Flow "{flow_name}" created and uploaded successfully',
                        'ready_for_use': False,
                        'publish_error': publish_result.get('error')
                    }
                
        except Exception as e:
            log_error(f"Error creating complete flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_flow_health_status(self) -> Dict:
        """Get overall flow system health status"""
        try:
            # Test API connectivity
            connectivity_test = self.test_api_connectivity()
            
            # List flows to check system status
            flows_result = self.list_flows()
            
            # Analyze flow status
            flow_analysis = {
                'total_flows': 0,
                'published_flows': 0,
                'draft_flows': 0,
                'flows_by_status': {}
            }
            
            if flows_result.get('success'):
                flows = flows_result.get('flows', [])
                flow_analysis['total_flows'] = len(flows)
                
                for flow in flows:
                    status = flow.get('status', 'UNKNOWN')
                    flow_analysis['flows_by_status'][status] = flow_analysis['flows_by_status'].get(status, 0) + 1
                    
                    if status == 'PUBLISHED':
                        flow_analysis['published_flows'] += 1
                    elif status == 'DRAFT':
                        flow_analysis['draft_flows'] += 1
            
            # Determine overall health
            overall_health = 'healthy'
            health_issues = []
            
            if not connectivity_test.get('api_access'):
                overall_health = 'critical'
                health_issues.append('API access failed')
            
            if not connectivity_test.get('business_account_access'):
                overall_health = 'critical'
                health_issues.append('Business account access failed')
            
            if not connectivity_test.get('flow_permissions'):
                overall_health = 'warning'
                health_issues.append('Flow permissions limited')
            
            if flow_analysis['total_flows'] == 0:
                overall_health = 'warning'
                health_issues.append('No flows configured')
            
            return {
                'success': True,
                'overall_health': overall_health,
                'api_connectivity': connectivity_test,
                'flow_analysis': flow_analysis,
                'health_issues': health_issues,
                'timestamp': datetime.now().isoformat(),
                'recommendations': self._generate_health_recommendations(connectivity_test, flow_analysis, health_issues)
            }
            
        except Exception as e:
            log_error(f"Error getting flow health status: {str(e)}")
            return {
                'success': False,
                'overall_health': 'critical',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_health_recommendations(self, connectivity: Dict, flow_analysis: Dict, issues: List[str]) -> List[str]:
        """Generate health recommendations based on system status"""
        recommendations = []
        
        if not connectivity.get('api_access'):
            recommendations.append('Check WhatsApp Access Token configuration and permissions')
        
        if not connectivity.get('business_account_access'):
            recommendations.append('Verify WhatsApp Business Account ID is correct')
        
        if not connectivity.get('flow_permissions'):
            recommendations.append('Request WhatsApp Flow permissions for your app')
        
        if flow_analysis.get('total_flows', 0) == 0:
            recommendations.append('Create your first WhatsApp Flow for trainer onboarding')
        
        if flow_analysis.get('draft_flows', 0) > 0 and flow_analysis.get('published_flows', 0) == 0:
            recommendations.append('Publish draft flows to make them available for users')
        
        if not recommendations:
            recommendations.append('WhatsApp Flow system is healthy and operational')
        
        return recommendations