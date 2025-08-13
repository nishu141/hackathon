import os
import re
import json
import sys
import asyncio
import logging
import subprocess
from typing import Dict, Any, List, Tuple
from datetime import datetime
from .base_agent import BaseAgent


class TestExecAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def _run_behave_tests(self, feature_path: str) -> tuple[int, str]:
        """Execute behave tests using subprocess."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "behave", feature_path, "--no-capture", "--format=plain"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode, result.stdout + result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.output
        except Exception as e:
            return 1, str(e)

    def _parse_behave_output(self, output: str, return_code: int) -> List[Dict[str, Any]]:
        """Parse behave output to extract detailed scenario results."""
        results: List[Dict[str, Any]] = []
        
        # Check if behave command failed completely
        if return_code != 0:
            # Parse error output for specific failures
            error_lines = [line.strip() for line in output.splitlines() if line.strip()]
            
            # Look for specific error patterns
            if "SyntaxError" in output:
                results.append({
                    "scenario": "Framework Setup",
                    "passed": False,
                    "error_type": "SyntaxError",
                    "error_details": "Python syntax error in test files",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            elif "ImportError" in output or "ModuleNotFoundError" in output:
                results.append({
                    "scenario": "Framework Setup",
                    "passed": False,
                    "error_type": "ImportError",
                    "error_details": "Missing dependencies or import issues",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            elif "AssertionError" in output or "Assertion Failed:" in output:
                results.append({
                    "scenario": "Test Execution",
                    "passed": False,
                    "error_type": "AssertionError",
                    "error_details": "Test assertions failed",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                results.append({
                    "scenario": "Test Execution",
                    "passed": False,
                    "error_type": "ExecutionError",
                    "error_details": f"Test execution failed with return code {return_code}",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            return results
        
        # Parse successful behave output
        current_scenario = None
        for line in output.splitlines():
            line = line.strip()
            
            # Detect scenario start
            if line.startswith("Scenario:"):
                scenario_name = line.split("Scenario:", 1)[1].strip()
                current_scenario = {
                    "scenario": scenario_name,
                    "passed": True,
                    "steps": [],
                    "timestamp": datetime.now().isoformat()
                }
                results.append(current_scenario)
            
            # Detect step results
            elif line.startswith("Given ") or line.startswith("When ") or line.startswith("Then "):
                if current_scenario:
                    step_result = {
                        "step": line,
                        "status": "passed",
                        "details": ""
                    }
                    current_scenario["steps"].append(step_result)
            
            # Detect step failures
            elif line.startswith("AssertionError:") or line.startswith("Assertion Failed:") or line.startswith("Failed step:"):
                if current_scenario:
                    current_scenario["passed"] = False
                    current_scenario["error_type"] = "AssertionError"
                    current_scenario["error_details"] = line
                    # Mark the last step as failed
                    if current_scenario["steps"]:
                        current_scenario["steps"][ -1 ]["status"] = "failed"
                        current_scenario["steps"][ -1 ]["details"] = line
            
            # Detect other errors
            elif "ERROR:" in line or "FAILED:" in line:
                if current_scenario:
                    current_scenario["passed"] = False
                    current_scenario["error_type"] = "ExecutionError"
                    current_scenario["error_details"] = line
        
        # If no scenarios were parsed, create a summary result
        if not results:
            if "passed" in output.lower() and "failed" not in output.lower():
                results.append({
                    "scenario": "Overall Test Execution",
                    "passed": True,
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                results.append({
                    "scenario": "Overall Test Execution",
                    "passed": False,
                    "error_type": "UnknownError",
                    "error_details": "Could not parse test results",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
        
        return results

    def _validate_test_environment(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the test environment is properly set up."""
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        orchestrator = state["orchestrator"]
        output_dir = orchestrator.output_dir
        
        # Check if framework directories exist
        required_dirs = ["features", "steps", "support"]  # behave expects "steps" directory
        for dir_name in required_dirs:
            dir_path = os.path.join(output_dir, dir_name)
            if not os.path.exists(dir_path):
                validation_result["valid"] = False
                validation_result["issues"].append(f"Missing directory: {dir_name}")
        
        # Check if feature file exists
        feature_path = state.get("feature_path", "")
        if not feature_path or not os.path.exists(feature_path):
            validation_result["valid"] = False
            validation_result["issues"].append(f"Feature file not found: {feature_path}")
        
        # Check if step definitions exist
        steps_dir = os.path.join(output_dir, "steps")  # behave expects "steps" directory
        if os.path.exists(steps_dir):
            step_files = [f for f in os.listdir(steps_dir) if f.endswith('.py')]
            if not step_files:
                validation_result["warnings"].append("No step definition files found")
        else:
            validation_result["valid"] = False
            validation_result["issues"].append("Missing steps directory")
        
        # Check if behave is available
        try:
            import behave
            validation_result["behave_available"] = True
        except ImportError:
            validation_result["valid"] = False
            validation_result["issues"].append("behave package not available")
        
        return validation_result

    def _analyze_test_failures(self, output: str) -> Dict[str, Any]:
        """Analyze test output to determine failure patterns and healing strategies"""
        output_lower = output.lower()
        
        # Check for specific error types
        if "ambiguousstep" in output_lower or "ambiguous step" in output_lower:
            return {
                "needs_healing": True,
                "recommended_healing": "ambiguous_step_repair",
                "failure_type": "ambiguous_step",
                "critical_issues": ["Duplicate step definitions detected"],
                "recommendations": ["Clean up old step definition files", "Regenerate step definitions"]
            }
        elif "syntaxerror" in output_lower or "syntax error" in output_lower:
            return {
                "needs_healing": True,
                "recommended_healing": "syntax_repair",
                "failure_type": "syntax",
                "critical_issues": ["Generated code has syntax errors"],
                "recommendations": ["Regenerate feature and step definitions", "Validate code syntax"]
            }
        elif "importerror" in output_lower or "module not found" in output_lower:
            return {
                "needs_healing": True,
                "recommended_healing": "import_repair",
                "failure_type": "import",
                "critical_issues": ["Required modules not available"],
                "recommendations": ["Install missing dependencies", "Check import paths"]
            }
        elif "assertionerror" in output_lower or "assertion failed" in output_lower:
            return {
                "needs_healing": True,
                "recommended_healing": "assertion_repair",
                "failure_type": "assertion",
                "critical_issues": ["Test assertions are failing"],
                "recommendations": ["Review test logic", "Update step definitions"]
            }
        elif "timeout" in output_lower or "timed out" in output_lower:
            return {
                "needs_healing": True,
                "recommended_healing": "timeout_repair",
                "failure_type": "timeout",
                "critical_issues": ["Test execution is timing out"],
                "recommendations": ["Increase timeout limits", "Check system performance"]
            }
        elif "max retries" in output_lower or "retry limit" in output_lower:
            return {
                "needs_healing": False,
                "recommended_healing": None,
                "failure_type": "retry_limit_exceeded",
                "critical_issues": ["Self-healing retry limit reached"],
                "recommendations": ["Manual intervention required", "Review system configuration"]
            }
        else:
            return {
                "needs_healing": True,
                "recommended_healing": "generic_repair",
                "failure_type": "unknown",
                "critical_issues": ["Unknown failure pattern"],
                "recommendations": ["Generic repair attempt", "Review logs for details"]
            }

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Behave tests and analyze results."""
        
        # Get paths from state
        feature_path = state.get("feature_path")
        steps_path = state.get("step_definitions_path")
        if not feature_path or not steps_path:
            self.logger.error("❌ No feature file or step definitions path provided")
            state["error"] = "Missing required paths"
            return state
            
        # Ensure only one step definitions file exists
        steps_dir = os.path.dirname(steps_path)
        for file in os.listdir(steps_dir):
            if file.endswith('.py') and file != os.path.basename(steps_path):
                os.remove(os.path.join(steps_dir, file))
                self.logger.info(f"Removed duplicate step file: {file}")
                
        # Run Behave tests
        return_code, output = self._run_behave_tests(feature_path)
        
        # Parse test results
        test_results = self._parse_behave_output(output, return_code)
        
        # Update state
        state.update({
            "test_executed": True,
            "test_exec_result": {
                "return_code": return_code,
                "output": output
            },
            "test_passed": return_code == 0,
            "scenario_results": test_results,
            "needs_self_heal": return_code != 0,
            "healing_attempts": state.get("healing_attempts", 0),
            "healing_types": [],
            "syntax_healed": False,
            "runtime_healed": False,
            "error_type": "execution_error" if return_code != 0 else None,
            "error_details": output if return_code != 0 else None,
            "error_specifics": test_results if return_code != 0 else None
        })
        
        return state