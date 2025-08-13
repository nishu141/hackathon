import os
from typing import Dict, Any
from datetime import datetime

class ReportAgent:
    def _generate_markdown_report(self, results, test_output, error_details=None, execution_log=None, execution_steps=None) -> str:
        report = [
            "# Test Execution Report", 
            "", 
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
            ""
        ]
        
        # Add step-by-step execution timeline
        if execution_steps:
            report.extend([
                "## Step-by-Step Execution Timeline",
                "",
                "| Time | Step | Details |",
                "|------|------|---------|"
            ])
            for step in execution_steps:
                timestamp = datetime.fromisoformat(step["timestamp"]).strftime('%H:%M:%S.%f')[:-3]
                step_name = step["step"]
                details = str(step.get("details", {})).replace("\n", "<br>")
                report.append(f"| {timestamp} | {step_name} | {details} |")
            report.append("")
        
        # Add execution log section
        if execution_log:
            report.extend([
                "## Execution Timeline",
                "",
                "| Timestamp | Event | Details |",
                "|-----------|-------|----------|"
            ])
            
            for entry in execution_log:
                timestamp = datetime.fromisoformat(entry["timestamp"]).strftime('%H:%M:%S.%f')[:-3]
                event = entry["event"]
                details = str(entry.get("details", "")).replace("\n", "<br>")
                report.append(f"| {timestamp} | {event} | {details} |")
            report.append("")
        
        if error_details:
            report.extend(["## Error Details", "", f"```\n{error_details}\n```", ""])
            
        report.extend(["## Scenario Results", ""])
        
        if results:
            for result in results:
                status = "✅ Passed" if result.get("passed") else "❌ Failed"
                report.extend([
                    f"### {result['scenario']}",
                    f"Status: {status}",
                    ""
                ])
                if not result.get("passed"):
                    report.extend([
                        "**Error Details:**",
                        "```",
                        result.get("error_details", "No error details available"),
                        "```",
                        ""
                    ])
                if "steps" in result:
                    report.extend(["**Steps:**", ""])
                    for step in result["steps"]:
                        step_status = "✅" if step["status"] == "passed" else "❌"
                        report.extend([f"{step_status} {step['step']}", ""])
                report.append("")
        else:
            report.extend(["No scenario results available", ""])
            
        if test_output:
            report.extend([
                "## Raw Test Output",
                "```",
                test_output,
                "```"
            ])
            
        return "\n".join(report)

    def _generate_html_report(self, results, test_output, error_details=None) -> str:
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>Test Execution Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            ".scenario { border: 1px solid #ddd; margin: 10px 0; padding: 10px; }",
            ".passed { background-color: #dff0d8; }",
            ".failed { background-color: #f2dede; }",
            ".step { margin: 5px 0; }",
            ".error { color: red; white-space: pre-wrap; }",
            "pre { background-color: #f5f5f5; padding: 10px; overflow-x: auto; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>Test Execution Report</h1>",
            f"<p>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        ]
        
        if error_details:
            html.extend([
                "<h2>Error Details</h2>",
                f"<pre class='error'>{error_details}</pre>"
            ])
        
        html.append("<h2>Scenario Results</h2>")
        
        if results:
            for result in results:
                status_class = "passed" if result.get("passed") else "failed"
                status_icon = "✅" if result.get("passed") else "❌"
                html.extend([
                    f"<div class='scenario {status_class}'>",
                    f"<h3>{result['scenario']} {status_icon}</h3>"
                ])
                
                if not result.get("passed"):
                    html.extend([
                        "<h4>Error Details:</h4>",
                        "<pre class='error'>",
                        result.get("error_details", "No error details available"),
                        "</pre>"
                    ])
                
                if "steps" in result:
                    html.append("<h4>Steps:</h4>")
                    for step in result["steps"]:
                        step_icon = "✅" if step["status"] == "passed" else "❌"
                        html.append(f"<div class='step'>{step_icon} {step['step']}</div>")
                html.append("</div>")
        else:
            html.append("<p>No scenario results available</p>")
            
        if test_output:
            html.extend([
                "<h2>Raw Test Output</h2>",
                "<pre>",
                test_output,
                "</pre>"
            ])
            
        html.extend(["</body>", "</html>"])
        return "\n".join(html)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator = state["orchestrator"]
        results = state.get("scenario_results", [])
        test_output = state.get("test_output", "")
        error_details = state.get("error_details")
        execution_log = state.get("execution_log", [])
        
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(orchestrator.output_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generate timestamp for report files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Add final execution status to log
        test_end_time = datetime.now()
        if state.get("test_start_time"):
            test_duration = (test_end_time - datetime.fromisoformat(state["test_start_time"])).total_seconds()
            execution_log.append({
                "timestamp": test_end_time.isoformat(),
                "event": "execution_complete",
                "details": {
                    "duration": f"{test_duration:.2f} seconds",
                    "final_status": "Passed" if state.get("test_passed") else "Failed",
                    "total_scenarios": len(results)
                }
            })
        
        # Generate and save Markdown report
        md_content = self._generate_markdown_report(results, test_output, error_details, execution_log)
        md_report_path = os.path.join(reports_dir, f"test_report_{timestamp}.md")
        with open(md_report_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        state["report_path"] = md_report_path
        
        # Generate and save HTML report
        html_content = self._generate_html_report(results, test_output, error_details)
        html_report_path = os.path.join(reports_dir, f"test_report_{timestamp}.html")
        with open(html_report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        state["html_report_path"] = html_report_path
        
        return state