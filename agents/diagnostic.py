import re
from typing import Dict, Any


class DiagnosticAgent:
    def _analyze_error_patterns(self, output: str) -> Dict[str, Any]:
        """Analyze error patterns in test output for detailed diagnosis."""
        analysis = {
            "error_type": None,
            "error_details": "",
            "severity": "low",
            "suggested_actions": [],
            "code_location": None
        }
        
        # Syntax errors
        if "SyntaxError:" in output:
            analysis["error_type"] = "SyntaxError"
            analysis["severity"] = "high"
            analysis["suggested_actions"] = [
                "Check Python syntax in step definition files",
                "Verify indentation and brackets",
                "Check for missing colons or parentheses"
            ]
            # Extract file and line information
            match = re.search(r'File "([^"]+)", line (\d+)', output)
            if match:
                analysis["code_location"] = f"{match.group(1)}:{match.group(2)}"
        
        # Import errors
        elif "ImportError:" in output or "ModuleNotFoundError:" in output:
            analysis["error_type"] = "ImportError"
            analysis["severity"] = "medium"
            analysis["suggested_actions"] = [
                "Install missing dependencies",
                "Check import statements",
                "Verify virtual environment activation"
            ]
            # Extract missing module
            match = re.search(r"No module named '([^']+)'", output)
            if match:
                analysis["error_details"] = f"Missing module: {match.group(1)}"
        
        # Assertion errors
        elif "AssertionError:" in output or "Assertion Failed:" in output:
            analysis["error_type"] = "AssertionError"
            analysis["severity"] = "medium"
            analysis["suggested_actions"] = [
                "Review test assertions",
                "Check API responses",
                "Verify test data and parameters",
                "Update expected values based on actual API behavior"
            ]
            # Extract assertion details
            match = re.search(r"(?:AssertionError|Assertion Failed): (.+)", output)
            if match:
                analysis["error_details"] = match.group(1)
        
        # Runtime errors
        elif "RuntimeError:" in output or "NameError:" in output or "AttributeError:" in output:
            analysis["error_type"] = "RuntimeError"
            analysis["severity"] = "medium"
            analysis["suggested_actions"] = [
                "Check variable definitions",
                "Verify object attributes",
                "Review step implementation logic"
            ]
        
        # Test execution failures
        elif "FAILED:" in output or "failed" in output.lower():
            analysis["error_type"] = "TestFailure"
            analysis["severity"] = "medium"
            analysis["suggested_actions"] = [
                "Review test scenarios",
                "Check API availability",
                "Verify test environment setup"
            ]
        
        # Framework setup issues
        elif "No such file or directory" in output:
            analysis["error_type"] = "FileSystemError"
            analysis["severity"] = "high"
            analysis["suggested_actions"] = [
                "Verify framework directory structure",
                "Check file paths and permissions",
                "Ensure all required files exist"
            ]
        
        # Timeout issues
        elif "timeout" in output.lower() or "timed out" in output.lower():
            analysis["error_type"] = "TimeoutError"
            analysis["severity"] = "medium"
            analysis["suggested_actions"] = [
                "Check API response times",
                "Increase timeout values",
                "Verify network connectivity"
            ]
        
        # Unknown errors
        else:
            analysis["error_type"] = "UnknownError"
            analysis["severity"] = "low"
            analysis["suggested_actions"] = [
                "Review complete error output",
                "Check system logs",
                "Verify environment configuration"
            ]
        
        return analysis

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test execution results and diagnose issues."""
        print("🔍 DiagnosticAgent: Starting error analysis...")
        
        output = state.get("test_exec_result", "")
        scenario_results = state.get("scenario_results", [])
        
        if not output and not scenario_results:
            print("🔍 DiagnosticAgent: No test results to analyze")
            state["diagnosed"] = True
            state["error_type"] = "NoResults"
            state["needs_self_heal"] = False
            return state
        
        # Analyze error patterns
        error_analysis = self._analyze_error_patterns(output)
        
        # Check scenario results for specific failures
        if scenario_results:
            failed_scenarios = [r for r in scenario_results if not r.get("passed", True)]
            if failed_scenarios:
                print(f"🔍 DiagnosticAgent: Found {len(failed_scenarios)} failed scenarios")
                
                # Get the first failure for detailed analysis
                first_failure = failed_scenarios[0]
                if first_failure.get("error_type"):
                    error_analysis["error_type"] = first_failure["error_type"]
                    error_analysis["error_details"] = first_failure.get("error_details", "")
                
                # Update error analysis based on scenario failures
                if "AssertionError" in str(first_failure):
                    error_analysis["error_type"] = "AssertionError"
                    error_analysis["severity"] = "medium"
                elif "ImportError" in str(first_failure):
                    error_analysis["error_type"] = "ImportError"
                    error_analysis["severity"] = "medium"
        
        # Determine if self-healing is needed
        needs_healing = error_analysis["error_type"] in [
            "SyntaxError", "ImportError", "RuntimeError", "FileSystemError", "AssertionError"
        ]
        
        # Log diagnosis results
        print(f"🔍 DiagnosticAgent: Error type: {error_analysis['error_type']}")
        print(f"🔍 DiagnosticAgent: Severity: {error_analysis['severity']}")
        if error_analysis["error_details"]:
            print(f"🔍 DiagnosticAgent: Details: {error_analysis['error_details']}")
        if error_analysis["code_location"]:
            print(f"🔍 DiagnosticAgent: Location: {error_analysis['code_location']}")
        
        if error_analysis["suggested_actions"]:
            print("🔍 DiagnosticAgent: Suggested actions:")
            for action in error_analysis["suggested_actions"]:
                print(f"  - {action}")
        
        # Update state
        state["diagnosed"] = True
        state["error_type"] = error_analysis["error_type"]
        state["error_details"] = error_analysis["error_details"]
        state["error_specifics"] = {
            "severity": error_analysis["severity"],
            "suggested_actions": error_analysis["suggested_actions"],
            "code_location": error_analysis["code_location"]
        }
        state["needs_self_heal"] = needs_healing
        
        print(f"🔍 DiagnosticAgent: Self-healing needed: {needs_healing}")
        
        return state