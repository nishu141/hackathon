import re
from typing import Dict, List, Optional
import os
import datetime

class StepGenerator:
    """Generates complete step definitions for BDD feature files"""
    
    def __init__(self):
        self.imports = [
            "from behave import given, when, then",
            "import requests",
            "import json",
            "import os",
            "import time"
        ]
        
        self.common_functions = {
            "load_config": '''
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'telecom_config.json')
    try:
        with open(config_path, 'r') as config_file:
            return json.load(config_file)
    except Exception as e:
        print(f'Config loading error: {e}')
        return {}
'''
        }

    def _get_step_type(self, step: str) -> str:
        """Determine the appropriate step type (given/when/then) for a step"""
        step_lower = step.lower().strip()
        
        if step_lower.startswith("given ") or "is configured" in step_lower:
            return "given"
        elif step_lower.startswith("when ") or "i send" in step_lower or step_lower.startswith("i "):
            return "when"
        else:
            return "then"

    def _generate_step_impl(self, step: str, step_type: str) -> str:
        """Generate the implementation for a step"""
        normalized = step.lower().strip()
        
        # Configuration step
        if "is configured" in normalized:
            return '''    """Setup the SMS API configuration for testing."""
    config = load_config()
    context.base_url = config.get('base_url', 'http://localhost:8000')
    context.api_key = config.get('api_key', 'test_key')
    context.headers = {'Authorization': f'Bearer {context.api_key}'}
    context.timeout = config.get('timeout', 10)
    context.retry_attempts = config.get('retry_attempts', 3)
    context.retry_delay = config.get('retry_delay', 1)'''

        # Send SMS step
        elif "send" in normalized and "sms" in normalized:
            return '''    """Send an SMS message to the specified recipient."""
    url = f'{context.base_url}/sms/send'
    data = {
        'recipient': recipient,
        'message': 'Test SMS message',
        'priority': 'normal'
    }
    
    # Implement retry logic
    attempts = context.retry_attempts if hasattr(context, 'retry_attempts') else 1
    for attempt in range(attempts):
        try:
            response = requests.post(url, json=data, headers=context.headers, timeout=context.timeout)
            context.response = response
            context.status_code = response.status_code
            if response.status_code == 200:
                break
            if attempt < attempts - 1:  # Don't sleep on last attempt
                time.sleep(context.retry_delay)
        except requests.exceptions.RequestException as e:
            context.response = None
            context.status_code = 500
            print(f'Error sending SMS (attempt {attempt + 1}): {e}')
            if attempt < attempts - 1:  # Don't sleep on last attempt
                time.sleep(context.retry_delay)'''

        # Status code verification
        elif "receive" in normalized and "response" in normalized:
            # Extract status code from step text
            status_code = int(re.search(r'\d+', step).group())
            return f'''    """Validate the response status code matches the expected value."""
    assert context.status_code == {status_code}, \\
        f'Expected status code {status_code}, got {{context.status_code}}' '''

        # Status code verification
        elif "receive" in normalized and "response" in normalized:
            return '''    """Validate the response status code matches the expected value."""
    assert context.status_code == status_code, \\
        f'Expected status code {status_code}, got {context.status_code}' '''

        # Message ID verification
        elif "message id" in normalized:
            return '''    """Verify the response contains a valid message ID."""
    assert context.response is not None, 'No response available for verification'
    try:
        response_data = context.response.json()
        assert 'message_id' in response_data, 'Response missing message_id'
        assert response_data['message_id'], 'Empty message_id received'
        context.message_id = response_data['message_id']
    except Exception as e:
        assert False, f'Could not verify message ID: {e}' '''

        # Default implementation
        return '    """TODO: Implement step."""\n    pass'

    def _extract_params(self, step: str) -> List[str]:
        """Extract parameter names from step definition"""
        return re.findall(r'\{([^}]+)\}', step)

    def _generate_func_name(self, step: str) -> str:
        """Generate a valid Python function name from step text"""
        # Remove parameters
        clean_step = re.sub(r'\{[^}]+\}', '', step)
        # Convert to snake case and clean up
        name = re.sub(r'[^a-zA-Z0-9]', '_', clean_step.lower())
        name = re.sub(r'_+', '_', name)
        return f"step_{name.strip('_')}"

    def generate_step_definition(self, step: str) -> str:
        """Generate a complete step definition including decorator and implementation"""
        step_type = self._get_step_type(step)
        params = self._extract_params(step)
        func_name = self._generate_func_name(step)
        
        # Prepare function signature
        param_list = ['context'] + params
        signature = ', '.join(param_list)
        
        # Generate the complete step
        # Use double quotes for steps with single quotes in them
        if "'" in step:
            decorator = f'@{step_type}("{step}")'
        else:
            decorator = f"@{step_type}('{step}')"
        func_def = f"def {func_name}({signature}):"
        implementation = self._generate_step_impl(step, step_type)
        
        return f"\n{decorator}\n{func_def}\n{implementation}\n"

    def generate_step_file(self, feature_steps: List[str], output_path: str) -> None:
        """Generate a complete step definitions file from a list of steps"""
        # Start with imports and common functions
        content = ["# AUTOGENERATED - DO NOT EDIT"] + self.imports
        content.extend([""] + list(self.common_functions.values()))
        
        # Generate step definitions
        for step in feature_steps:
            content.append(self.generate_step_definition(step))
            
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
