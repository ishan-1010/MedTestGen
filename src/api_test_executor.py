"""
API Test Executor for Healthcare Test Case Generation Platform
Executes API tests directly within the application
"""

import requests
import json
import time
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import streamlit as st
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class APITestExecutor:
    """Execute API tests with healthcare compliance validation"""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        """
        Initialize API Test Executor
        
        Args:
            base_url: Base URL for API endpoints
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or "https://api.healthconnect.com/v2"
        self.timeout = timeout
        self.session = requests.Session()
        self.results = []
        
        # Default headers for healthcare APIs
        self.default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'HealthConnect-TestRunner/1.0'
        }
    
    def set_authentication(self, auth_type: str, credentials: Dict):
        """
        Set authentication for API requests
        
        Args:
            auth_type: Type of authentication (bearer, api_key, basic, oauth)
            credentials: Authentication credentials
        """
        if auth_type == 'bearer':
            self.session.headers['Authorization'] = f"Bearer {credentials.get('token', '')}"
        elif auth_type == 'api_key':
            if credentials.get('header_name'):
                self.session.headers[credentials['header_name']] = credentials.get('key', '')
            else:
                self.session.headers['X-API-Key'] = credentials.get('key', '')
        elif auth_type == 'basic':
            self.session.auth = (credentials.get('username', ''), credentials.get('password', ''))
        elif auth_type == 'oauth':
            self.session.headers['Authorization'] = f"Bearer {credentials.get('access_token', '')}"
    
    def execute_test(self, test_case: Dict) -> Dict:
        """
        Execute a single API test case
        
        Args:
            test_case: Test case dictionary with API details
            
        Returns:
            Test execution result
        """
        result = {
            'test_id': test_case.get('id', 'unknown'),
            'test_title': test_case.get('title', 'Unknown Test'),
            'category': test_case.get('category', 'API'),
            'status': 'pending',
            'request': {},
            'response': {},
            'assertions': [],
            'execution_time': 0,
            'timestamp': datetime.now().isoformat(),
            'compliance_checks': []
        }
        
        try:
            # Extract API details from test case
            test_data = test_case.get('test_data', {})
            
            # Determine endpoint and method
            endpoint = test_data.get('endpoint', '/health')
            method = test_data.get('method', 'GET').upper()
            
            # Build full URL
            if endpoint.startswith('http'):
                url = endpoint
            else:
                url = urljoin(self.base_url, endpoint.lstrip('/'))
            
            # Prepare request
            headers = {**self.default_headers, **test_data.get('headers', {})}
            params = test_data.get('params', {})
            body = test_data.get('body', {})
            
            # Store request details
            result['request'] = {
                'method': method,
                'url': url,
                'headers': self._sanitize_headers(headers),
                'params': params,
                'body': body
            }
            
            # Execute request
            start_time = time.time()
            
            if method == 'GET':
                response = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, json=body, params=params, timeout=self.timeout)
            elif method == 'PUT':
                response = self.session.put(url, headers=headers, json=body, params=params, timeout=self.timeout)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers, params=params, timeout=self.timeout)
            elif method == 'PATCH':
                response = self.session.patch(url, headers=headers, json=body, params=params, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            execution_time = time.time() - start_time
            
            # Store response details
            result['response'] = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': self._parse_response_body(response),
                'response_time_ms': round(execution_time * 1000, 2)
            }
            
            result['execution_time'] = execution_time
            
            # Run assertions
            assertions = self._run_assertions(test_case, response, execution_time)
            result['assertions'] = assertions
            
            # Healthcare compliance checks
            compliance_checks = self._run_compliance_checks(test_case, response)
            result['compliance_checks'] = compliance_checks
            
            # Determine overall status
            failed_assertions = [a for a in assertions if not a['passed']]
            failed_compliance = [c for c in compliance_checks if not c['passed']]
            
            if failed_assertions or failed_compliance:
                result['status'] = 'failed'
            else:
                result['status'] = 'passed'
            
        except requests.exceptions.Timeout:
            result['status'] = 'failed'
            result['error'] = f"Request timed out after {self.timeout} seconds"
        except requests.exceptions.ConnectionError as e:
            result['status'] = 'failed'
            result['error'] = f"Connection error: {str(e)}"
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logger.error(f"Test execution error: {e}")
        
        self.results.append(result)
        return result
    
    def _sanitize_headers(self, headers: Dict) -> Dict:
        """Sanitize headers to hide sensitive information"""
        sanitized = {}
        sensitive_headers = ['authorization', 'x-api-key', 'api-key', 'token', 'cookie']
        
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                # Show only first 4 and last 4 characters
                if len(value) > 10:
                    sanitized[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    sanitized[key] = "***hidden***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _parse_response_body(self, response):
        """Parse response body based on content type"""
        content_type = response.headers.get('Content-Type', '')
        
        try:
            if 'application/json' in content_type:
                return response.json()
            elif 'text/' in content_type:
                return response.text
            elif 'application/xml' in content_type:
                return response.text
            else:
                # For binary content, just show size
                return f"<Binary content: {len(response.content)} bytes>"
        except:
            return response.text if response.text else "<Empty response>"
    
    def _run_assertions(self, test_case: Dict, response: requests.Response, execution_time: float) -> List[Dict]:
        """Run test assertions"""
        assertions = []
        expected = test_case.get('expected_results', '')
        
        # Default assertions based on expected results string
        if 'status 200' in expected.lower() or 'successful' in expected.lower():
            assertions.append({
                'type': 'status_code',
                'expected': 200,
                'actual': response.status_code,
                'passed': response.status_code == 200,
                'message': f"Expected status 200, got {response.status_code}"
            })
        elif 'status 201' in expected.lower() or 'created' in expected.lower():
            assertions.append({
                'type': 'status_code',
                'expected': 201,
                'actual': response.status_code,
                'passed': response.status_code == 201,
                'message': f"Expected status 201, got {response.status_code}"
            })
        elif 'status 404' in expected.lower() or 'not found' in expected.lower():
            assertions.append({
                'type': 'status_code',
                'expected': 404,
                'actual': response.status_code,
                'passed': response.status_code == 404,
                'message': f"Expected status 404, got {response.status_code}"
            })
        
        # Response time assertion
        if execution_time > 2.0:
            assertions.append({
                'type': 'response_time',
                'expected': '< 2 seconds',
                'actual': f"{execution_time:.2f} seconds",
                'passed': False,
                'message': f"Response time exceeded 2 seconds"
            })
        else:
            assertions.append({
                'type': 'response_time',
                'expected': '< 2 seconds',
                'actual': f"{execution_time:.2f} seconds",
                'passed': True,
                'message': "Response time within acceptable range"
            })
        
        # Content type assertion for JSON APIs
        content_type = response.headers.get('Content-Type', '')
        if 'json' in test_case.get('title', '').lower() or 'api' in test_case.get('category', '').lower():
            assertions.append({
                'type': 'content_type',
                'expected': 'application/json',
                'actual': content_type,
                'passed': 'application/json' in content_type,
                'message': f"Expected JSON response, got {content_type}"
            })
        
        # Check for required fields in response
        if response.status_code < 400:
            try:
                json_response = response.json()
                if isinstance(json_response, dict):
                    # Check for common required fields
                    if 'appointment' in test_case.get('title', '').lower():
                        required_fields = ['id', 'status']
                        for field in required_fields:
                            assertions.append({
                                'type': 'required_field',
                                'expected': f"Field '{field}' present",
                                'actual': field in json_response,
                                'passed': field in json_response,
                                'message': f"Checking for required field: {field}"
                            })
            except:
                pass
        
        return assertions
    
    def _run_compliance_checks(self, test_case: Dict, response: requests.Response) -> List[Dict]:
        """Run healthcare compliance checks"""
        checks = []
        compliance = test_case.get('compliance', [])
        
        # HIPAA compliance checks
        if 'HIPAA' in compliance:
            # Check for HTTPS
            checks.append({
                'standard': 'HIPAA',
                'check': 'HTTPS encryption',
                'passed': response.url.startswith('https'),
                'message': 'PHI must be transmitted over HTTPS'
            })
            
            # Check for authentication
            auth_header = response.request.headers.get('Authorization')
            checks.append({
                'standard': 'HIPAA',
                'check': 'Authentication required',
                'passed': auth_header is not None,
                'message': 'API requests must be authenticated'
            })
            
            # Check audit headers
            audit_headers = ['X-Request-ID', 'X-Correlation-ID']
            has_audit = any(h in response.headers for h in audit_headers)
            checks.append({
                'standard': 'HIPAA',
                'check': 'Audit trail headers',
                'passed': has_audit,
                'message': 'Requests should include audit trail headers'
            })
        
        # GDPR compliance checks
        if 'GDPR' in compliance:
            # Check for rate limiting
            rate_limit_header = response.headers.get('X-RateLimit-Limit')
            checks.append({
                'standard': 'GDPR',
                'check': 'Rate limiting',
                'passed': rate_limit_header is not None,
                'message': 'API should implement rate limiting'
            })
        
        # FDA compliance checks
        if 'FDA' in compliance or 'FDA 21 CFR Part 11' in compliance:
            # Check for version headers
            version_header = response.headers.get('API-Version')
            checks.append({
                'standard': 'FDA 21 CFR Part 11',
                'check': 'API versioning',
                'passed': version_header is not None,
                'message': 'API should include version information'
            })
        
        return checks
    
    def execute_test_suite(self, test_cases: List[Dict]) -> Dict:
        """
        Execute multiple test cases
        
        Args:
            test_cases: List of test cases to execute
            
        Returns:
            Summary of test execution results
        """
        summary = {
            'total': len(test_cases),
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'execution_time': 0,
            'results': []
        }
        
        start_time = time.time()
        
        for test_case in test_cases:
            # Only execute API/Integration tests
            if test_case.get('category') in ['API', 'Integration', 'Performance']:
                result = self.execute_test(test_case)
                summary['results'].append(result)
                
                if result['status'] == 'passed':
                    summary['passed'] += 1
                elif result['status'] == 'failed':
                    summary['failed'] += 1
                else:
                    summary['errors'] += 1
        
        summary['execution_time'] = time.time() - start_time
        summary['pass_rate'] = (summary['passed'] / summary['total'] * 100) if summary['total'] > 0 else 0
        
        return summary
    
    def generate_html_report(self, summary: Dict) -> str:
        """Generate HTML report of test execution"""
        html = f"""
        <html>
        <head>
            <title>API Test Execution Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .passed {{ color: green; font-weight: bold; }}
                .failed {{ color: red; font-weight: bold; }}
                .error {{ color: orange; font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #4CAF50; color: white; }}
                .test-passed {{ background: #d4edda; }}
                .test-failed {{ background: #f8d7da; }}
                .test-error {{ background: #fff3cd; }}
            </style>
        </head>
        <body>
            <h1>API Test Execution Report</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p>Total Tests: {summary['total']}</p>
                <p class="passed">Passed: {summary['passed']}</p>
                <p class="failed">Failed: {summary['failed']}</p>
                <p class="error">Errors: {summary['errors']}</p>
                <p>Pass Rate: {summary['pass_rate']:.1f}%</p>
                <p>Execution Time: {summary['execution_time']:.2f} seconds</p>
            </div>
            
            <h2>Test Results</h2>
            <table>
                <tr>
                    <th>Test ID</th>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Response Time</th>
                    <th>Assertions</th>
                    <th>Compliance</th>
                </tr>
        """
        
        for result in summary['results']:
            status_class = f"test-{result['status']}"
            assertions_passed = sum(1 for a in result.get('assertions', []) if a['passed'])
            assertions_total = len(result.get('assertions', []))
            compliance_passed = sum(1 for c in result.get('compliance_checks', []) if c['passed'])
            compliance_total = len(result.get('compliance_checks', []))
            
            html += f"""
                <tr class="{status_class}">
                    <td>{result['test_id']}</td>
                    <td>{result['test_title']}</td>
                    <td>{result['status'].upper()}</td>
                    <td>{result['response'].get('response_time_ms', 'N/A')} ms</td>
                    <td>{assertions_passed}/{assertions_total}</td>
                    <td>{compliance_passed}/{compliance_total}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        return html

# Demo/Mock API Server for testing
class MockHealthcareAPI:
    """Mock Healthcare API for demonstration"""
    
    @staticmethod
    def handle_request(endpoint: str, method: str, body: Dict = None) -> Tuple[int, Dict]:
        """
        Mock API endpoint handler
        
        Returns:
            Tuple of (status_code, response_body)
        """
        # Mock endpoints
        if endpoint == '/health':
            return 200, {"status": "healthy", "version": "2.0.0"}
        
        elif endpoint == '/appointments' and method == 'GET':
            return 200, {
                "data": [
                    {
                        "id": "apt_123",
                        "patient_id": "pat_456",
                        "provider_id": "doc_789",
                        "start_time": "2024-01-15T10:00:00Z",
                        "status": "confirmed"
                    }
                ],
                "meta": {"total": 1}
            }
        
        elif endpoint == '/appointments' and method == 'POST':
            if body and body.get('patient_id'):
                return 201, {
                    "id": f"apt_{datetime.now().timestamp()}",
                    "patient_id": body['patient_id'],
                    "status": "booked",
                    "created_at": datetime.now().isoformat()
                }
            else:
                return 400, {"error": "Missing required field: patient_id"}
        
        elif '/appointments/' in endpoint and method == 'DELETE':
            return 204, {}
        
        elif endpoint == '/patients' and method == 'GET':
            return 200, {
                "data": [
                    {
                        "id": "pat_456",
                        "name": "Test Patient",
                        "mrn": "MRN123456",
                        "date_of_birth": "1990-01-01"
                    }
                ]
            }
        
        elif endpoint == '/auth/token' and method == 'POST':
            return 200, {
                "access_token": "mock_token_abc123",
                "token_type": "Bearer",
                "expires_in": 3600
            }
        
        else:
            return 404, {"error": "Endpoint not found"}
