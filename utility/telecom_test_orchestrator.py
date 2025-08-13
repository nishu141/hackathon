import asyncio
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

class TelecomTestOrchestrator:
    def __init__(self, output_dir: str = "./telecom_api_bdd", config_path: str = "utility/telecom_config.json", user_story: str = None, debug: bool = False, max_healing_attempts: int = 5, enable_auto_healing: bool = True):
        self.output_dir = output_dir
        self.config_path = config_path
        self.user_story = user_story or "As a telecom user, I want to verify mobile data usage API"
        self.debug = debug
        self.max_retries = max_healing_attempts
        self.enable_auto_healing = enable_auto_healing
        
        self.api_config = self._load_config()
        self.base_url = self.api_config.get("base_url", "http://localhost:8000")
        self.parameters = self.api_config.get("parameters", {})
        self.logger = self._setup_logger()
        self.retry_count = 0
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for the orchestrator"""
        logger = logging.getLogger("Orchestrator")
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not logger.handlers:
            logger.addHandler(handler)
        return logger
        
    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return config.get("api", {})
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    async def generate_from_user_story(self, user_story: str) -> str:
        """Generate feature file from user story"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        feature_path = os.path.join(self.output_dir, "features", f"test_feature_{timestamp}.feature")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(feature_path), exist_ok=True)
        
        content = self.generate_feature_content(user_story)
        
        with open(feature_path, 'w') as f:
            f.write(content)
        
        self.logger.info(f"✅ Generated feature file: {feature_path}")
        return feature_path

    def generate_feature_content(self, user_story: str, probe: Optional[Dict[str, Any]] = None) -> str:
        user_story_lower = user_story.lower()
        
        # Build 3 priority scenarios per domain
        scenarios: List[Tuple[str, List[str]]] = []
        if 'sms' in user_story_lower or 'message' in user_story_lower:
            feature_name = "SMS API Testing"
            scenarios = [
                ("P0 - Send SMS successfully", [
                    "Given the SMS API is configured",
                    "When I send an SMS message to '{recipient}'",
                    "Then I should receive a 200 response",
                    "And The response should contain message ID",
                ]),
                ("P1 - Send SMS with invalid recipient", [
                    "Given the SMS API is configured",
                    "When I send an SMS message to '{recipient}'",
                    "Then I should receive a 400 response",
                ]),
                ("P2 - Retry send SMS flow", [
                    "Given the SMS API is configured",
                    "When I send an SMS message to '{recipient}'",
                    "Then I should receive a 200 response",
                ]),
            ]
        elif 'mobile data' in user_story_lower or 'data usage' in user_story_lower:
            feature_name = "Mobile Data Usage API Testing"
            scenarios = [
                ("P0 - Check data usage for valid user", [
                    "Given the Mobile Data API is configured",
                    "When I request data usage for user '{user_id}'",
                    "Then I should receive a 200 response",
                    "And The response should contain usage data",
                ]),
                ("P1 - Check data usage for invalid user", [
                    "Given the Mobile Data API is configured",
                    "When I request data usage for user '{user_id}'",
                    "Then I should receive a 404 response",
                ]),
                ("P2 - Check data usage stability", [
                    "Given the Mobile Data API is configured",
                    "When I request data usage for user '{user_id}'",
                    "Then I should receive a 200 response",
                ]),
            ]
        elif 'user' in user_story_lower:
            feature_name = "User Management API Testing"
            scenarios = [
                ("P0 - Fetch user information with valid ID", [
                    "Given the API is configured",
                    "When I request user with ID '{user_id}'",
                    "Then I should receive a 200 response",
                    "And The response should contain user data",
                ]),
                ("P1 - Fetch user information with invalid ID", [
                    "Given the API is configured",
                    "When I request user with ID '{user_id}'",
                    "Then I should receive a 404 response",
                ]),
                ("P2 - Fetch user information again for stability", [
                    "Given the API is configured",
                    "When I request user with ID '{user_id}'",
                    "Then I should receive a 200 response",
                ]),
            ]
        else:
            feature_name = "API Functionality Testing"
            scenarios = [
                ("P0 - API responds with valid data", [
                    "Given the API is configured",
                    'When I make a request to the API',
                    "Then I should receive a 200 response",
                    "And The response should contain valid data",
                ]),
                ("P1 - API handles not found", [
                    "Given the API is configured",
                    'When I make a request to the API',
                    "Then I should receive a 404 response",
                ]),
                ("P2 - API responds under load", [
                    "Given the API is configured",
                    'When I make a request to the API',
                    "Then I should receive a 200 response",
                ]),
            ]
        
        param_lines = "\n".join([f"#   {k}: {v}" for k, v in self.parameters.items()])
        content_lines = [
            "# AUTOGENERATED - DO NOT EDIT",
            f'# Generated from: "{user_story}"',
            f"# Testing API: {self.api_config.get('name', 'API')} ({self.base_url})",
            param_lines,
            "",
            f"Feature: {feature_name}",
            "",
        ]
        
        for scenario_name, steps in scenarios:
            content_lines.append(f"Scenario: {scenario_name}")
            for step in steps:
                content_lines.append(f"    {step}")
            content_lines.append("")
        
        return "\n".join(content_lines) + "\n"

    async def generate_step_definitions(self, user_story: str = None) -> str:
        """Generate step definitions file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        steps_path = os.path.join(self.output_dir, "steps", f"test_steps_{timestamp}.py")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(steps_path), exist_ok=True)
        
        # Clean up old step definition files to prevent conflicts
        self._cleanup_old_step_files()
        
        content = self.generate_step_definitions_content(user_story)

        # Write orchestrator-generated content first
        with open(steps_path, 'w') as f:
            f.write(content)

        # Now run agent logic to append missing stubs
        try:
            from utility.agents.content_gen import ContentGenAgent
            agent = ContentGenAgent()
            state = {"orchestrator": self, "user_story": user_story}
            await agent.run(state)
        except Exception as e:
            self.logger.warning(f"⚠️ Could not run agent for stub generation: {e}")

        self.logger.info(f"✅ Generated step definitions: {steps_path}")
        return steps_path

    def _cleanup_old_step_files(self):
        """Remove old step definition files to prevent AmbiguousStep errors"""
        steps_dir = os.path.join(self.output_dir, "steps")
        if os.path.exists(steps_dir):
            for file in os.listdir(steps_dir):
                if file.startswith("test_steps_") and file.endswith(".py"):
                    file_path = os.path.join(steps_dir, file)
                    try:
                        os.remove(file_path)
                        self.logger.info(f"🧹 Cleaned up old step file: {file}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Could not remove {file}: {e}")

    def generate_step_definitions_content(self, user_story: str = None) -> str:
        # Collect all unique step phrases from all scenarios
        if user_story:
            user_story_lower = user_story.lower()
        else:
            user_story_lower = "user"

        # Get all scenarios and steps
        scenarios = []
        if 'sms' in user_story_lower or 'message' in user_story_lower:
            scenarios = [
                ["Given the SMS API is configured", "When I send an SMS message to '{recipient}'", "Then I should receive a {status_code:d} response", "And The response should contain message ID"],
                ["Given the SMS API is configured", "When I send an SMS message to '{recipient}'", "Then I should receive a {status_code:d} response"],
                ["Given the SMS API is configured", "When I send an SMS message to '{recipient}'", "Then I should receive a {status_code:d} response"],
            ]
        elif 'mobile data' in user_story_lower or 'data usage' in user_story_lower:
            scenarios = [
                ["Given the Mobile Data API is configured", "When I request data usage for user '{user_id}'", "Then I should receive a {status_code:d} response", "And The response should contain usage data"],
                ["Given the Mobile Data API is configured", "When I request data usage for user '{user_id}'", "Then I should receive a {status_code:d} response"],
                ["Given the Mobile Data API is configured", "When I request data usage for user '{user_id}'", "Then I should receive a {status_code:d} response"],
            ]
        elif 'user' in user_story_lower:
            scenarios = [
                ["Given the API is configured", "When I request user with ID '{user_id}'", "Then I should receive a {status_code:d} response", "And The response should contain user data"],
                ["Given the API is configured", "When I request user with ID '{user_id}'", "Then I should receive a {status_code:d} response"],
                ["Given the API is configured", "When I request user with ID '{user_id}'", "Then I should receive a {status_code:d} response"],
            ]
        else:
            scenarios = [
                ["Given the API is configured", 'When I make a request to the API', "Then I should receive a {status_code:d} response", "And The response should contain valid data"],
                ["Given the API is configured", 'When I make a request to the API', "Then I should receive a {status_code:d} response"],
                ["Given the API is configured", 'When I make a request to the API', "Then I should receive a {status_code:d} response"],
            ]
        # Flatten and deduplicate step phrases
        step_phrases = set()
        for scenario in scenarios:
            for step in scenario:
                step_phrases.add(step)

        # Map step phrases to step implementations (single quotes for parameters)
        step_impls = {
            "Given the SMS API is configured": "@given('the SMS API is configured')\ndef step_sms_api_configured(context):\n    context.config.update(load_config())\n    context.base_url = context.config.get('base_url', 'http://localhost:8000')\n    context.api_key = context.config.get('api_key', 'test_key')\n    print(f'SMS API configured with base URL: {context.base_url}')\n",
            "When I send an SMS message to '{recipient}'": "@when('I send an SMS message to '{recipient}')\ndef step_send_sms(context, recipient):\n    url = f'{context.base_url}/sms/send'\n    headers = {'Authorization': f'Bearer {context.api_key}'}\n    data = {'recipient': recipient, 'message': 'Test SMS message'}\n    try:\n        response = requests.post(url, json=data, headers=headers, timeout=10)\n        context.response = response\n        context.status_code = response.status_code\n    except Exception as e:\n        print(f'Error sending SMS: {e}')\n        context.response = None\n        context.status_code = 500\n",
            "Then I should receive a {status_code:d} response": "@then('I should receive a {status_code:d} response')\ndef step_verify_status_code(context, status_code):\n    assert context.status_code == status_code, f'Expected {status_code}, got {context.status_code}'\n",
            "And The response should contain message ID": "@then('The response should contain message ID')\ndef step_verify_message_id(context):\n    if context.response:\n        try:\n            response_data = context.response.json()\n            assert 'message_id' in response_data, 'Response missing message_id'\n        except Exception as e:\n            assert False, f'Could not verify message ID: {e}'\n    else:\n        assert False, 'No response available for verification'\n",
            "Given the Mobile Data API is configured": "@given('the Mobile Data API is configured')\ndef step_mobile_data_api_configured(context):\n    context.config.update(load_config())\n    context.base_url = context.config.get('base_url', 'http://localhost:8000')\n    context.api_key = context.config.get('api_key', 'test_key')\n    print(f'Mobile Data API configured with base URL: {context.base_url}')\n",
            "When I request data usage for user '{user_id}'": "@when('I request data usage for user '{user_id}')\ndef step_request_data_usage(context, user_id):\n    url = f'{context.base_url}/data/usage/{user_id}'\n    headers = {'Authorization': f'Bearer {context.api_key}'}\n    try:\n        response = requests.get(url, headers=headers, timeout=10)\n        context.response = response\n        context.status_code = response.status_code\n    except Exception as e:\n        context.response = None\n        context.status_code = 500\n",
            "And The response should contain usage data": "@then('The response should contain usage data')\ndef step_verify_usage_data(context):\n    if context.response:\n        try:\n            response_data = context.response.json()\n            assert 'usage_data' in response_data, 'Response missing usage_data'\n        except Exception as e:\n            assert False, f'Could not verify usage data: {e}'\n    else:\n        assert False, 'No response available for verification'\n",
            "Given the API is configured": "@given('the API is configured')\ndef step_api_configured(context):\n    context.config.update(load_config())\n    context.base_url = context.config.get('base_url', 'http://localhost:8000')\n    context.api_key = context.config.get('api_key', 'test_key')\n",
            "When I request user with ID '{user_id}'": "@when('I request user with ID '{user_id}')\ndef step_request_user(context, user_id):\n    url = f'{context.base_url}/users/{user_id}'\n    headers = {'Authorization': f'Bearer {context.api_key}'}\n    try:\n        response = requests.get(url, headers=headers, timeout=10)\n        context.response = response\n        context.status_code = response.status_code\n    except Exception as e:\n        context.response = None\n        context.status_code = 500\n",
            "And The response should contain user data": "@then('The response should contain user data')\ndef step_verify_user_data(context):\n    if context.response:\n        try:\n            response_data = context.response.json()\n            assert 'user_data' in response_data or 'data' in response_data, 'Response missing user data'\n        except Exception as e:\n            assert False, f'Could not verify user data: {e}'\n    else:\n        assert False, 'No response available for verification'\n",
            "When I make a request to the API": "@when('I make a request to the API')\ndef step_make_api_request(context):\n    url = f'{context.base_url}/test'\n    headers = {'Authorization': f'Bearer {context.api_key}'}\n    try:\n        response = requests.get(url, headers=headers, timeout=10)\n        context.response = response\n        context.status_code = response.status_code\n    except Exception as e:\n        context.response = None\n        context.status_code = 500\n",
            "And The response should contain valid data": "@then('The response should contain valid data')\ndef step_verify_valid_data(context):\n    if context.response:\n        try:\n            response_data = context.response.json()\n            assert response_data is not None, 'Response data is None'\n        except Exception as e:\n            assert False, f'Could not verify valid data: {e}'\n    else:\n        assert False, 'No response available for verification'\n",
        }
        for scenario in scenarios:
            for step in scenario:
                step_phrases.add(step)

        # Map step phrases to step implementations
        step_impls = {
            "Given the SMS API is configured":
                "@given('the SMS API is configured')\ndef step_sms_api_configured(context):\n    context.config = load_config()\n    context.base_url = context.config.get('base_url', 'http://localhost:8000')\n    context.api_key = context.config.get('api_key', 'test_key')\n    print(f'SMS API configured with base URL: {context.base_url}')\n",
            'When I send an SMS message to "{recipient}"':
                "@when('I send an SMS message to \"{recipient}\"')\ndef step_send_sms(context, recipient):\n    url = f'{context.base_url}/sms/send'\n    headers = {'Authorization': f'Bearer {context.api_key}'}\n    data = {'recipient': recipient, 'message': 'Test SMS message'}\n    try:\n        response = requests.post(url, json=data, headers=headers, timeout=10)\n        context.response = response\n        context.status_code = response.status_code\n    except Exception as e:\n        print(f'Error sending SMS: {e}')\n        context.response = None\n        context.status_code = 500\n",
            "Then I should receive a {status_code:d} response":
                "@then('I should receive a {status_code:d} response')\ndef step_verify_status_code(context, status_code):\n    assert context.status_code == status_code, f'Expected {status_code}, got {context.status_code}'\n",
            "And The response should contain message ID":
                "@then('The response should contain message ID')\ndef step_verify_message_id(context):\n    if context.response:\n        try:\n            response_data = context.response.json()\n            assert 'message_id' in response_data, 'Response missing message_id'\n        except Exception as e:\n            assert False, f'Could not verify message ID: {e}'\n    else:\n        assert False, 'No response available for verification'\n",
            "Given the Mobile Data API is configured":
                "@given('the Mobile Data API is configured')\ndef step_mobile_data_api_configured(context):\n    context.config = load_config()\n    context.base_url = context.config.get('base_url', 'http://localhost:8000')\n    context.api_key = context.config.get('api_key', 'test_key')\n    print(f'Mobile Data API configured with base URL: {context.base_url}')\n",
            'When I request data usage for user "{user_id}"':
                "@when('I request data usage for user '{user_id}')\ndef step_request_data_usage(context, user_id):\n    url = f'{context.base_url}/data/usage/{user_id}'\n    headers = {'Authorization': f'Bearer {context.api_key}'}\n    try:\n        response = requests.get(url, headers=headers, timeout=10)\n        context.response = response\n        context.status_code = response.status_code\n    except Exception as e:\n        context.response = None\n        context.status_code = 500\n",
            "And The response should contain usage data":
                "@then('The response should contain usage data')\ndef step_verify_usage_data(context):\n    if context.response:\n        try:\n            response_data = context.response.json()\n            assert 'usage_data' in response_data, 'Response missing usage_data'\n        except Exception as e:\n            assert False, f'Could not verify usage data: {e}'\n    else:\n        assert False, 'No response available for verification'\n",
            "Given the API is configured":
                "@given('the API is configured')\ndef step_api_configured(context):\n    context.config = load_config()\n    context.base_url = context.config.get('base_url', 'http://localhost:8000')\n    context.api_key = context.config.get('api_key', 'test_key')\n",
            'When I request user with ID "{user_id}"':
                "@when('I request user with ID '{user_id}')\ndef step_request_user(context, user_id):\n    url = f'{context.base_url}/users/{user_id}'\n    headers = {'Authorization': f'Bearer {context.api_key}'}\n    try:\n        response = requests.get(url, headers=headers, timeout=10)\n        context.response = response\n        context.status_code = response.status_code\n    except Exception as e:\n        context.response = None\n        context.status_code = 500\n",
            "And The response should contain user data":
                "@then('The response should contain user data')\ndef step_verify_user_data(context):\n    if context.response:\n        try:\n            response_data = context.response.json()\n            assert 'user_data' in response_data or 'data' in response_data, 'Response missing user data'\n        except Exception as e:\n            assert False, f'Could not verify user data: {e}'\n    else:\n        assert False, 'No response available for verification'\n",
            'When I make a request to the API':
                "@when('I make a request to the API')\ndef step_make_api_request(context):\n    url = f'{context.base_url}/test'\n    headers = {'Authorization': f'Bearer {context.api_key}'}\n    try:\n        response = requests.get(url, headers=headers, timeout=10)\n        context.response = response\n        context.status_code = response.status_code\n    except Exception as e:\n        context.response = None\n        context.status_code = 500\n",
            "And The response should contain valid data":
                "@then('The response should contain valid data')\ndef step_verify_valid_data(context):\n    if context.response:\n        try:\n            response_data = context.response.json()\n            assert response_data is not None, 'Response data is None'\n        except Exception as e:\n            assert False, f'Could not verify valid data: {e}'\n    else:\n        assert False, 'No response available for verification'\n",
        }

        # Compose the step definitions file
        base_steps = (
            "# AUTOGENERATED - DO NOT EDIT\n"
            "from behave import given, when, then\n"
            "import requests\n"
            "import json, os, time\n"
            "\n"
            "def load_config():\n"
            "    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'telecom_config.json')\n"
            "    try:\n"
            "        with open(config_path, 'r') as config_file:\n"
            "            config = json.load(config_file)\n"
            "        return config['api']\n"
            "    except Exception as e:\n"
            "        print(f'Config loading error: {e}')\n"
            "        return {}\n"
            "\n"
        )

        step_code = [base_steps]
        for phrase in sorted(step_phrases):
            if phrase in step_impls:
                step_code.append(step_impls[phrase])

        return "\n".join(step_code)

    async def detect_existing_framework(self) -> Dict[str, Any]:
        """Detect if BDD framework already exists"""
        try:
            # Check if output directory exists
            if not os.path.exists(self.output_dir):
                return {
                    "valid": False,
                    "path": self.output_dir,
                    "type": None,
                    "found_directories": [],
                    "missing_directories": ["features", "steps", "support"],
                    "issues": ["Output directory does not exist"]
                }
            
            # Check for required directories
            required_dirs = ["features", "steps", "support"]
            found_dirs = []
            missing_dirs = []
            
            for dir_name in required_dirs:
                dir_path = os.path.join(self.output_dir, dir_name)
                if os.path.exists(dir_path):
                    found_dirs.append(dir_name)
                else:
                    missing_dirs.append(dir_name)
            
            # Check if behave is available using python -m behave
            import sys
            try:
                subprocess.run([sys.executable, "-m", "behave", "--version"], capture_output=True, check=True)
                behave_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                behave_available = False
            
            # Determine framework type
            if found_dirs and behave_available:
                framework_type = "behave-python"
                valid = True
                issues = []
            else:
                framework_type = None
                valid = False
                issues = []
                if not behave_available:
                    issues.append("behave not available")
                if missing_dirs:
                    issues.append(f"Missing directories: {', '.join(missing_dirs)}")
            
            return {
                "valid": valid,
                "path": self.output_dir,
                "type": framework_type,
                "found_directories": found_dirs,
                "missing_directories": missing_dirs,
                "issues": issues
            }
            
        except Exception as e:
            return {
                "valid": False,
                "path": self.output_dir,
                "type": None,
                "found_directories": [],
                "missing_directories": ["features", "steps", "support"],
                "issues": [f"Error detecting framework: {str(e)}"]
            }

    async def generate_report(self, scenario_results: List[Dict[str, Any]]) -> str:
        """Generate a test report from scenario results (Markdown)"""
        try:
            report_dir = os.path.join(self.output_dir, "reports")
            os.makedirs(report_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = os.path.join(report_dir, f"test_report_{timestamp}.md")
            
            # Generate report content
            report_content = [
                "# Telecom API Test Report",
                f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**API**: {self.api_config.get('name', 'Unknown API')}",
                f"**Base URL**: {self.base_url}",
                "",
                "## Summary"
            ]
            
            # Count results
            total = len(scenario_results) if scenario_results else 0
            if total > 0:
                passed = sum(1 for r in scenario_results if r.get('passed', False))
                failed = total - passed
                success_rate = (passed / total) * 100
                
                report_content.extend([
                    f"- **Total Scenarios**: {total}",
                    f"- **Passed**: {passed}",
                    f"- **Failed**: {failed}",
                    f"- **Success Rate**: {success_rate:.1f}%",
                    ""
                ])
            else:
                report_content.extend([
                    "- **Total Scenarios**: 0",
                    "- **Status**: No test results available",
                    ""
                ])
            
            # Add scenario details if available
            if scenario_results:
                report_content.append("## Scenario Details")
                for i, result in enumerate(scenario_results, 1):
                    status = "✅ PASSED" if result.get('passed', False) else "❌ FAILED"
                    report_content.append(f"### Scenario {i}: {status}")
                    report_content.append(f"- **Description**: {result.get('scenario', 'No description')}")
                    
                    if 'error_details' in result and result['error_details']:
                        report_content.append(f"- **Error**: {result['error_details']}")
                    
                    if 'steps' in result and result['steps']:
                        report_content.append("- **Steps**:")
                        for step in result['steps']:
                            step_status = "✅" if step.get('status') == 'passed' else "❌"
                            report_content.append(f"  - {step_status} {step.get('step', 'Unknown step')}")
                    
                    report_content.append("")
            
            # Write report
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_content))
            
            self.logger.info(f"Generated report at: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate report: {str(e)}")
            return ""

    async def generate_html_report(self, scenario_results: List[Dict[str, Any]], raw_output: str = "") -> str:
        """Generate an HTML report covering all executed scenarios"""
        report_dir = os.path.join(self.output_dir, "reports")
        os.makedirs(report_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_path = os.path.join(report_dir, f"test_report_{timestamp}.html")
        
        def esc(s: str) -> str:
            return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        total = len(scenario_results) if scenario_results else 0
        passed = sum(1 for r in (scenario_results or []) if r.get('passed'))
        failed = total - passed
        success_rate = (passed / total) * 100 if total else 0.0
        
        rows = []
        if scenario_results:
            for r in scenario_results:
                status = "PASSED" if r.get('passed') else "FAILED"
                color = "#d1fadf" if r.get('passed') else "#fde2e4"
                steps_html = ""
                for st in r.get('steps', []) or []:
                    steps_html += f"<li>{esc(st.get('step',''))} - <strong>{esc(st.get('status',''))}</strong></li>"
                err = esc(r.get('error_details',''))
                rows.append(
                    f"<tr><td>{esc(r.get('scenario',''))}</td><td style='background:{color}'>{status}</td>"
                    f"<td><ul>{steps_html}</ul></td><td><pre style='white-space:pre-wrap'>{err}</pre></td></tr>"
                )
        
        html = f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Telecom API Test Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
h1 {{ margin-bottom: 0; }}
.small {{ color: #666; margin-top: 4px; }}
.summary {{ margin: 16px 0; padding: 12px; background: #f6f8fa; border-radius: 8px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
th {{ background: #f0f0f0; }}
pre {{ background: #f8f8f8; padding: 8px; border-radius: 4px; }}
</style>
</head>
<body>
  <h1>Telecom API Test Report</h1>
  <div class="small">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
  <div class="small">API: {esc(self.api_config.get('name', 'Unknown API'))} | Base URL: {esc(self.base_url)}</div>
  <div class="summary">
    <strong>Summary</strong>
    <div>Total Scenarios: {total}</div>
    <div>Passed: {passed}</div>
    <div>Failed: {failed}</div>
    <div>Success Rate: {success_rate:.1f}%</div>
  </div>
  <h2>Scenarios</h2>
  <table>
    <thead><tr><th>Scenario</th><th>Status</th><th>Steps</th><th>Error Details</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <h2>Raw Output</h2>
  <pre>{esc(raw_output)}</pre>
</body>
</html>
"""
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        self.logger.info(f"Generated HTML report at: {html_path}")
        return html_path

    async def initialize_framework(self) -> Tuple[bool, Dict[str, Any]]:
        """Initialize the BDD framework"""
        try:
            # Create required directories
            required_dirs = ["features", "steps", "support", "reports"]
            created_dirs = []
            
            for dir_name in required_dirs:
                dir_path = os.path.join(self.output_dir, dir_name)
                os.makedirs(dir_path, exist_ok=True)
                created_dirs.append(dir_name)
            
            # Create environment.py file
            env_path = os.path.join(self.output_dir, "support", "environment.py")
            env_content = '''# AUTOGENERATED - DO NOT EDIT
from behave import fixture
import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

@fixture
def setup_environment(context):
    """Setup test environment"""
    context.config = {
        "base_url": "http://localhost:8000",
        "timeout": 10
    }
    yield context.config

def before_scenario(context, scenario):
    """Setup before each scenario"""
    pass

def after_scenario(context, scenario):
    """Cleanup after each scenario"""
    pass
'''
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            # Create requirements.txt
            req_path = os.path.join(self.output_dir, "requirements.txt")
            req_content = '''# AUTOGENERATED - DO NOT EDIT
behave>=1.2.6
requests>=2.25.1
pytest>=6.0.0
'''
            with open(req_path, 'w', encoding='utf-8') as f:
                f.write(req_content)
            
            # Create README.md
            readme_path = os.path.join(self.output_dir, "README.md")
            readme_content = f'''# AUTOGENERATED - DO NOT EDIT
# Telecom API Test Framework

This framework was automatically generated for testing the Telecom API.

## Configuration
- API Config: {self.config_path}
- Base URL: {self.base_url}
- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Running Tests
```bash
cd {self.output_dir}
behave features/
```
'''
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            self.logger.info(f"✓ Created README.md: {readme_path}")
            
            # Verify framework creation
            verification = await self.detect_existing_framework()
            if verification['valid']:
                self.logger.info("✓ Framework initialization verified successfully")
                return True, {
                    'type': 'behave-python',
                    'path': self.output_dir,
                    'status': 'success',
                    'created_directories': created_dirs,
                    'created_files': [env_path, req_path, readme_path]
                }
            else:
                self.logger.error("✗ Framework verification failed after creation")
                return False, {
                    'error': 'Framework verification failed',
                    'verification_result': verification
                }
                
        except Exception as e:
            self.logger.error(f"Framework init failed: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False, {'error': str(e)}

    async def execute_test(self, feature_path: str = None) -> Tuple[bool, str]:
        """Execute test with retry limit and cleanup"""
        if self.retry_count >= self.max_retries:
            self.logger.warning(f"❌ Max retries ({self.max_retries}) reached. Stopping self-healing loop.")
            return False, f"Max retries ({self.max_retries}) reached. Self-healing failed."
        
        self.retry_count += 1
        self.logger.info(f"🔄 Attempt {self.retry_count}/{self.max_retries}")
        
        # Validate test environment
        env_status = self._validate_test_environment()
        if not env_status["valid"]:
            return False, f"Environment validation failed: {env_status['issues']}"
        
        # Clean up old step files before execution
        self._cleanup_old_step_files()
        # Always generate step definitions before running tests
        await self.generate_step_definitions(self.user_story)
        
        # Execute behave command using python -m behave
        import sys
        cmd = [sys.executable, "-m", "behave", feature_path, "--no-capture", "--format=plain"]
        self.logger.info(f"🚀 Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=".",
                timeout=60
            )
            
            full_output = result.stdout + result.stderr
            self.logger.info(f"📊 Behave execution completed with return code: {result.returncode}")
            
            # Parse output for failures
            parse_result = self._parse_behave_output(full_output)
            
            if parse_result["success"]:
                self.logger.info("✅ All tests passed!")
                return True, full_output
            else:
                self.logger.warning(f"❌ Test execution failed: {parse_result['failure_reason']}")
                
                # Attempt self-healing if we haven't exceeded max retries
                if self.retry_count < self.max_retries:
                    self.logger.info("🔧 Attempting self-healing...")
                    healing_result = await self._attempt_scenario_healing(parse_result, feature_path)
                    
                    if healing_result.get("healed", False):
                        self.logger.info("✅ Self-healing successful, re-running tests...")
                        return await self.execute_test(feature_path)
                    else:
                        self.logger.warning("❌ Self-healing failed")
                        return False, full_output
                else:
                    self.logger.warning("❌ Max retries reached, stopping self-healing")
                    return False, full_output
                    
        except subprocess.TimeoutExpired:
            error_msg = "Test execution timed out after 60 seconds"
            self.logger.error(f"⏰ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Test execution error: {str(e)}"
            self.logger.error(f"💥 {error_msg}")
            return False, error_msg

    def _validate_test_environment(self) -> Dict[str, Any]:
        """Validate test environment before execution"""
        issues = []
        
        # Check if behave is installed using python -m behave
        import sys
        try:
            subprocess.run([sys.executable, "-m", "behave", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            issues.append("behave not installed or not accessible")
        
        # Check if feature file exists
        if not os.path.exists(os.path.join(self.output_dir, "features")):
            issues.append("features directory not found")
        
        # Check if steps directory exists
        if not os.path.exists(os.path.join(self.output_dir, "steps")):
            issues.append("steps directory not found")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    def _parse_behave_output(self, output: str) -> Dict[str, Any]:
        """Parse behave output to identify failures and their types"""
        lines = output.split('\n')
        
        # Check for common failure patterns
        if "AssertionError" in output:
            return {
                "success": False,
                "failure_type": "assertion",
                "failure_reason": "Assertion failed in test execution",
                "details": [line for line in lines if "AssertionError" in line]
            }
        elif "ImportError" in output or "ModuleNotFoundError" in output:
            return {
                "success": False,
                "failure_type": "import",
                "failure_reason": "Module import failed",
                "details": [line for line in lines if any(err in line for err in ["ImportError", "ModuleNotFoundError"])]
            }
        elif "SyntaxError" in output:
            return {
                "success": False,
                "failure_type": "syntax",
                "failure_reason": "Syntax error in generated code",
                "details": [line for line in lines if "SyntaxError" in line]
            }
        elif "AmbiguousStep" in output:
            return {
                "success": False,
                "failure_type": "ambiguous_step",
                "failure_reason": "Duplicate step definitions found",
                "details": [line for line in lines if "AmbiguousStep" in line]
            }
        elif "FAILED" in output or "failed" in output:
            return {
                "success": False,
                "failure_type": "execution",
                "failure_reason": "Test execution failed",
                "details": [line for line in lines if "FAILED" in line or "failed" in line]
            }
        
        # If no specific failure patterns found, assume success
        return {"success": True, "failure_type": None, "failure_reason": None, "details": []}

    async def _attempt_scenario_healing(self, parse_result: Dict[str, Any], feature_path: str) -> Dict[str, Any]:
        """Diagnose and fix errors in real time, applying targeted fixes for each error type."""
        failure_type = parse_result.get("failure_type")
        details = parse_result.get("details", [])
        healed = False
        method = None
        error = None

        if failure_type == "ambiguous_step":
            # Remove duplicate step definitions
            steps_dir = os.path.join(self.output_dir, "steps")
            for file in os.listdir(steps_dir):
                if file.startswith("test_steps_") and file.endswith(".py") and "reqres" not in file:
                    try:
                        os.remove(os.path.join(steps_dir, file))
                        self.logger.info(f"Removed duplicate step file: {file}")
                        healed = True
                        method = "ambiguous_step_cleanup"
                    except Exception as e:
                        error = str(e)
            # Remove __pycache__ if exists
            pycache_dir = os.path.join(steps_dir, "__pycache__")
            if os.path.exists(pycache_dir):
                for f in os.listdir(pycache_dir):
                    try:
                        os.remove(os.path.join(pycache_dir, f))
                    except Exception:
                        pass
                try:
                    os.rmdir(pycache_dir)
                except Exception:
                    pass
            return {"healed": healed, "method": method, "error": error}

        elif failure_type == "syntax":
            # Attempt to fix syntax errors by analyzing details
            # For demo, just log and ask for manual fix
            self.logger.warning(f"Syntax error detected: {details}")
            return {"healed": False, "method": "syntax_manual_fix", "error": details}

        elif failure_type == "import":
            # Install missing packages
            try:
                subprocess.run(["pip", "install", "behave", "requests"], check=True)
                healed = True
                method = "dependency_installation"
            except Exception as e:
                error = str(e)
            return {"healed": healed, "method": method, "error": error}

        elif failure_type == "assertion":
            # Patch assertion logic if possible
            self.logger.warning(f"Assertion error detected: {details}")
            # For demo, just log and ask for manual fix
            return {"healed": False, "method": "assertion_manual_fix", "error": details}

        elif failure_type == "execution":
            # Generic runtime error, log and ask for manual fix
            self.logger.warning(f"Runtime error detected: {details}")
            return {"healed": False, "method": "runtime_manual_fix", "error": details}

        else:
            # If no specific error, try generic repair (regenerate files)
            self.logger.info("Attempting generic repair...")
            self._cleanup_old_step_files()
            user_story = self.user_story or "Sample Reqres API test"
            await self.generate_from_user_story(user_story)
            await self.generate_step_definitions(user_story)
            return {"healed": True, "method": "generic_repair"}

    async def _repair_ambiguous_step_issues(self) -> Dict[str, Any]:
        """Repair ambiguous step definition issues"""
        self.logger.info("🔧 Repairing ambiguous step definitions...")
        
        # Clean up ALL old step files
        self._cleanup_old_step_files()
        
        # Regenerate step definitions with current user story
        try:
            # Get the current user story from state or use default
            user_story = "User to test sms sending feature of the API"  # Default fallback
            await self.generate_step_definitions(user_story)
            return {"healed": True, "method": "ambiguous_step_cleanup"}
        except Exception as e:
            self.logger.error(f"❌ Failed to repair ambiguous step issues: {e}")
            return {"healed": False, "method": "ambiguous_step_cleanup", "error": str(e)}

    async def _repair_syntax_issues(self) -> Dict[str, Any]:
        """Repair syntax issues in generated code"""
        self.logger.info("🔧 Repairing syntax issues...")
        
        try:
            # Regenerate both feature and step definitions
            user_story = "User to test sms sending feature of the API"
            await self.generate_from_user_story(user_story)
            await self.generate_step_definitions(user_story)
            return {"healed": True, "method": "syntax_regeneration"}
        except Exception as e:
            self.logger.error(f"❌ Failed to repair syntax issues: {e}")
            return {"healed": False, "method": "syntax_regeneration", "error": str(e)}

    async def _repair_import_issues(self) -> Dict[str, Any]:
        """Repair import issues"""
        self.logger.info("🔧 Repairing import issues...")
        
        try:
            # Install required dependencies
            subprocess.run(["pip", "install", "behave", "requests"], check=True)
            return {"healed": True, "method": "dependency_installation"}
        except Exception as e:
            self.logger.error(f"❌ Failed to repair import issues: {e}")
            return {"healed": False, "method": "dependency_installation", "error": str(e)}

    async def _repair_assertion_failures(self) -> Dict[str, Any]:
        """Repair assertion failures"""
        self.logger.info("🔧 Repairing assertion failures...")
        
        try:
            # Regenerate step definitions with more flexible assertions
            user_story = "User to test sms sending feature of the API"
            await self.generate_step_definitions(user_story)
            return {"healed": True, "method": "assertion_repair"}
        except Exception as e:
            self.logger.error(f"❌ Failed to repair assertion failures: {e}")
            return {"healed": False, "method": "assertion_repair", "error": str(e)}

    async def _generic_repair(self) -> Dict[str, Any]:
        """Generic repair strategy"""
        self.logger.info("🔧 Attempting generic repair...")
        
        try:
            # Clean up and regenerate everything
            self._cleanup_old_step_files()
            
            user_story = "User to test sms sending feature of the API"
            await self.generate_from_user_story(user_story)
            return {"healed": True, "method": "generic_repair"}
        except Exception as e:
            self.logger.error(f"❌ Generic repair failed: {e}")
            return {"healed": False, "method": "generic_repair", "error": str(e)}
