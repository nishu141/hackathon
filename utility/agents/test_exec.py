#!/usr/bin/env python3

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

__all__ = ['TestExecAgent']


class TestExecAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.execution_steps = []
        self.step_timings = {}
        
    def _log_step(self, step_name: str, details: Dict[str, Any] = None):
        """Log a step execution with timing and details"""
        timestamp = datetime.now()
        step_info = {
            "step": step_name,
            "timestamp": timestamp.isoformat(),
            "details": details or {}
        }
        self.execution_steps.append(step_info)
        self.step_timings[step_name] = timestamp
        self.logger.info(f"Step: {step_name} - {json.dumps(details, indent=2) if details else 'No details'}")
        
    def _run_behave_tests(self, feature_path: str) -> tuple[int, str, List[Dict[str, Any]]]:
        """Execute behave tests using subprocess with detailed logging."""
        execution_log = []
        try:
            # Log test start
            start_time = datetime.now()
            execution_log.append({
                "timestamp": start_time.isoformat(),
                "event": "test_start",
                "details": {"feature_path": feature_path}
            })
            
            # Check feature file exists
            if not os.path.exists(feature_path):
                execution_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "event": "error",
                    "details": {"error": f"Feature file not found: {feature_path}"}
                })
                return 1, f"Feature file not found: {feature_path}", execution_log
            
            # Log feature file content
            try:
                with open(feature_path, 'r') as f:
                    feature_content = f.read()
                    execution_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "event": "feature_file_read",
                        "details": {"content": feature_content}
                    })
            except Exception as e:
                execution_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "event": "error",
                    "details": {"error": f"Failed to read feature file: {str(e)}"}
                })
            
            # Execute behave with detailed output
            command = [sys.executable, "-m", "behave", feature_path, 
                      "--no-capture", "--format=plain", "--show-timings"]
            
            execution_log.append({
                "timestamp": datetime.now().isoformat(),
                "event": "command_start",
                "details": {"command": " ".join(command)}
            })
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False
            )
            
            output = result.stdout + result.stderr
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Log execution details
            execution_log.append({
                "timestamp": end_time.isoformat(),
                "event": "command_complete",
                "details": {
                    "return_code": result.returncode,
                    "duration": duration,
                    "output": output
                }
            })
            
            self.logger.info("=" * 80)
            self.logger.info(f"Test Execution Summary:")
            self.logger.info(f"Feature: {feature_path}")
            self.logger.info(f"Duration: {duration:.2f} seconds")
            self.logger.info(f"Return Code: {result.returncode}")
            self.logger.info("=" * 80)
            self.logger.info("Detailed Output:")
            self.logger.info(output)
            self.logger.info("=" * 80)
            
            return result.returncode, output, execution_log
            
        except subprocess.CalledProcessError as e:
            error_details = f"Behave execution failed: {str(e)}"
            execution_log.append({
                "timestamp": datetime.now().isoformat(),
                "event": "error",
                "details": {"error": error_details}
            })
            self.logger.error(error_details)
            return e.returncode, e.output, execution_log
            
        except Exception as e:
            error_details = f"Unexpected error during test execution: {str(e)}"
            execution_log.append({
                "timestamp": datetime.now().isoformat(),
                "event": "error",
                "details": {"error": error_details}
            })
            self.logger.error(error_details)
            return 1, str(e), execution_log

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run test execution with detailed step tracking"""
        self._log_step("test_execution_start", {
            "user_story": state.get("user_story"),
            "feature_path": state.get("feature_path")
        })
        
        # Initialize state with detailed execution tracking
        start_time = datetime.now()
        state.update({
            "test_passed": False,
            "test_executed": False,
            "test_exec_result": None,
            "scenario_results": [],
            "needs_self_heal": False,
            "error_type": None,
            "error_details": None,
            "error_specifics": {},
            "current_step": "test_exec",
            "execution_log": [],
            "test_start_time": start_time.isoformat(),
            "execution_steps": self.execution_steps,
            "step_timings": self.step_timings
        })
        
        # Log initial state
        state["execution_log"].append({
            "timestamp": state["test_start_time"],
            "event": "execution_start",
            "details": {
                "user_story": state.get("user_story"),
                "feature_path": state.get("feature_path"),
                "step_definitions_path": state.get("step_definitions_path")
            }
        })
        
        # Validate project paths
        if not state.get("feature_path"):
            error_msg = "Feature file path not found"
            state.update({
                "error_type": "missing_path",
                "error_details": error_msg,
                "execution_log": state["execution_log"] + [{
                    "timestamp": datetime.now().isoformat(),
                    "event": "error",
                    "details": {"error": error_msg}
                }]
            })
            return state
        
        # Run behave tests with detailed logging
        exit_code, output, test_execution_log = self._run_behave_tests(state["feature_path"])
        state["execution_log"].extend(test_execution_log)
        
        # Parse results and analyze failures with detailed logging
        scenario_results = self._parse_behave_output(output, exit_code)
        
        # Log parsing results
        state["execution_log"].append({
            "timestamp": datetime.now().isoformat(),
            "event": "results_parsed",
            "details": {
                "num_scenarios": len(scenario_results),
                "scenarios": scenario_results
            }
        })
        
        # Add failure analysis
        error_patterns = {
            "config_not_found": (r"No such file or directory: .*telecom_config\.json", "Configuration file not found"),
            "connection_refused": (r"Connection refused.*localhost:8000", "SMS API service not running"),
            "undefined_steps": (r"undefined.*step", "Missing step definitions"),
            "syntax_error": (r"SyntaxError", "Python syntax error in test files"),
            "assertion_error": (r"AssertionError", "Test assertion failed"),
            "import_error": (r"ImportError|ModuleNotFoundError", "Missing Python module")
        }
        
        # Analyze failures
        failure_analysis = {
            "failure_type": "unknown",
            "critical_issues": [],
            "needs_healing": True,
            "error_type": None,
            "error_details": None
        }
        
        # Check for error patterns
        for error_type, (pattern, desc) in error_patterns.items():
            if re.search(pattern, output, re.IGNORECASE):
                failure_analysis["failure_type"] = error_type
                failure_analysis["critical_issues"].append(desc)
                failure_analysis["error_type"] = error_type
                failure_analysis["error_details"] = desc
                break
        
        # Update state with results
        state.update({
            "test_output": output,
            "test_executed": True,
            "test_passed": exit_code == 0,
            "test_exec_result": exit_code,
            "scenario_results": scenario_results,
            "failure_analysis": failure_analysis,
            "needs_self_heal": exit_code != 0,
            "error_type": failure_analysis.get("error_type", "test_failure") if exit_code != 0 else None,
            "error_details": failure_analysis.get("error_details", output) if exit_code != 0 else None
        })
        
        return state

    def _parse_behave_output(self, output: str, return_code: int) -> List[Dict[str, Any]]:
        """Parse behave output to extract detailed scenario results."""
        results = []
        
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
                        current_scenario["steps"][-1]["status"] = "failed"
                        current_scenario["steps"][-1]["details"] = line
            
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
