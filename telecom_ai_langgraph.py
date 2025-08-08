# telecom_ai_langgraph.py
import asyncio
import os
import json
import argparse
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from langgraph.graph import StateGraph, END
from state import AgentState

from agents.framework_init import FrameworkInitAgent
from agents.content_gen import ContentGenAgent
from agents.test_exec import TestExecAgent
from agents.diagnostic import DiagnosticAgent
from agents.syntax_selfheal import SyntaxSelfHealAgent
from agents.runtime_selfheal import RuntimeSelfHealAgent
from agents.validation import ValidationAgent
from agents.report import ReportAgent
from agents.human_review import HumanReviewAgent

from logging_config import setup_logger
from telecom_test_orchestrator import TelecomTestOrchestrator

logger = setup_logger()


def create_default_config(config_path: str):
    config = {
        "api": {
            "name": "ReqRes Demo API",
            "base_url": "https://reqres.in/api",
            "description": "Public API for testing",
            "endpoints": {
                "user": "/users/{user_id}",
                "resource": "/unknown/{resource_id}",
            },
            "parameters": {
                "valid_user_id": "2",
                "invalid_user_id": "23",
                "valid_resource_id": "2",
            },
        }
    }
    os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    logger.info("Created default config at: %s", config_path)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Resilient Telecom Test Automation")
    parser.add_argument(
        "user_story",
        nargs="?",
        default="As a telecom user, I want to verify mobile data usage API",
        help="User story describing test scenario",
    )
    parser.add_argument("--config", default="/workspace/telecom_config.json")
    parser.add_argument("--max-healing", type=int, default=3)
    parser.add_argument("--disable-auto-healing", action="store_true")
    parser.add_argument("--output-dir", default="/workspace/telecom_api_bdd")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    if not os.path.exists(args.config):
        create_default_config(args.config)
    return args


class ExtendedOrchestrator(TelecomTestOrchestrator):
    def __init__(self, output_dir: str, config_path: str, debug: bool = False,
                 max_healing_attempts: int = 3, enable_auto_healing: bool = True):
        super().__init__(output_dir, config_path, debug)
        self.max_healing_attempts = max_healing_attempts
        self.enable_auto_healing = enable_auto_healing
        self.healing_log: List[Dict[str, Any]] = []

    async def generate_report(self, scenario_results):
        report_path = os.path.join(self.output_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        total = len(scenario_results) if scenario_results else 0
        passed = len([r for r in scenario_results if r.get("passed", True)]) if scenario_results else 0
        data = {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "success_rate": round((passed / total) * 100, 2) if total else 0,
            },
            "scenarios": scenario_results or [],
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Generated JSON report: %s", report_path)
        return report_path


def create_initial_state(args: argparse.Namespace) -> AgentState:
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    enable_auto_healing = not args.disable_auto_healing
    orchestrator = ExtendedOrchestrator(
        output_dir=output_dir,
        config_path=args.config,
        debug=args.verbose,
        max_healing_attempts=args.max_healing,
        enable_auto_healing=enable_auto_healing,
    )
    return {
        "orchestrator": orchestrator,
        "config_path": args.config,
        "user_story": args.user_story,
        "logger": logger,
        "test_passed": False,
        "manual_review": False,
        "framework_details": {},
        "framework_initialized": False,
        "feature_path": "",
        "step_definitions_path": "",
        "syntax_healed": False,
        "runtime_healed": False,
        "validation_completed": False,
        "report_path": "",
        "error_details": None,
        "test_executed": False,
        "scenario_results": [],
        "needs_self_heal": False,
        "healing_attempts": 0,
        "healing_types": [],
        "current_step": "STARTUP",
        "execution_trail": [{"timestamp": datetime.now(timezone.utc).isoformat(), "step": "INIT", "status": "STARTED"}],
        "diagnosed": False,
        "error_type": None,
        "error_specifics": {},
        "max_healing_attempts": args.max_healing,
        "enable_auto_healing": enable_auto_healing,
        "test_exec_result": "",
    }


def create_workflow():
    graph = StateGraph(AgentState)
    agent_classes = {
        "framework_init": FrameworkInitAgent(),
        "content_gen": ContentGenAgent(),
        "test_exec": TestExecAgent(),
        "diagnostic": DiagnosticAgent(),
        "syntax_selfheal": SyntaxSelfHealAgent(),
        "runtime_selfheal": RuntimeSelfHealAgent(),
        "validation": ValidationAgent(),
        "human_review": HumanReviewAgent(),
        "report": ReportAgent(),
    }

    def tracked_agent(name):
        async def run_tracked(state: AgentState) -> dict:
            state["current_step"] = name
            state["execution_trail"].append({"timestamp": datetime.now(timezone.utc).isoformat(), "step": name, "status": "STARTED"})
            logger.info("[START] STEP: %s", name)
            try:
                result = await agent_classes[name].run(state)
                logger.info("[COMPLETED] STEP: %s", name)
                state["execution_trail"][-1]["status"] = "COMPLETED"
                return result if isinstance(result, dict) else {}
            except Exception as e:
                logger.exception("[ERROR] STEP: %s - %s", name, str(e))
                state["execution_trail"][-1]["status"] = f"FAILED: {str(e)}"
                error_type = type(e).__name__
                error_details = str(e)
                tb = traceback.extract_tb(e.__traceback__)
                last_frame = tb[-1] if tb else None
                file_path = last_frame.filename if last_frame else "unknown"
                line_number = last_frame.lineno if last_frame else 0
                return {
                    "error_details": error_details,
                    "error_type": error_type,
                    "file_path": file_path,
                    "line_number": line_number,
                    "manual_review": True,
                    "test_passed": False,
                    "needs_self_heal": True,
                }
        return run_tracked

    for name in agent_classes:
        graph.add_node(name, tracked_agent(name))

    graph.set_entry_point("framework_init")
    graph.add_edge("framework_init", "content_gen")
    graph.add_edge("content_gen", "test_exec")

    def after_test_exec(state: AgentState) -> str:
        results = state.get("scenario_results", [])
        if results and all(r.get("passed", True) for r in results):
            return "validation"
        if state.get("enable_auto_healing", True) and state.get("healing_attempts", 0) < state.get("max_healing_attempts", 3):
            return "diagnostic"
        return "human_review"

    def after_diagnostic(state: AgentState) -> str:
        et = state.get("error_type", "")
        if not et:
            return "human_review"
        if "Syntax" in et or "Indentation" in et or "Import" in et:
            return "syntax_selfheal"
        if "Runtime" in et or "Name" in et:
            return "runtime_selfheal"
        return "human_review"

    graph.add_conditional_edges("test_exec", after_test_exec, {
        "validation": "validation",
        "diagnostic": "diagnostic",
        "human_review": "human_review",
    })
    graph.add_conditional_edges("diagnostic", after_diagnostic, {
        "syntax_selfheal": "syntax_selfheal",
        "runtime_selfheal": "runtime_selfheal",
        "human_review": "human_review",
    })

    graph.add_edge("syntax_selfheal", "test_exec")
    graph.add_edge("runtime_selfheal", "test_exec")

    graph.add_edge("validation", "report")
    graph.add_edge("human_review", "report")
    graph.add_edge("report", END)

    return graph.compile()


async def run_main_workflow(initial_state: AgentState):
    workflow = create_workflow()
    logger.info("Starting test automation workflow")
    state = await workflow.ainvoke(initial_state)
    if state.get("scenario_results"):
        try:
            report_path = await state["orchestrator"].generate_report(state["scenario_results"])
            logger.info("Report: %s", report_path)
        except Exception as e:
            logger.error("Report generation failed: %s", str(e))
    return state


if __name__ == "__main__":
    args = parse_arguments()
    banner = f"""
    ============================================================
    TELECOM TEST AUTOMATION | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    User Story: {args.user_story}
    Configuration: {args.config}
    Max Healing Attempts: {args.max_healing}
    Auto-Healing: {'Enabled' if not args.disable_auto_healing else 'Disabled'}
    Output Directory: {args.output_dir}
    ============================================================
    """
    print(banner)
    logger.info(banner.strip())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    exit_code = 0
    try:
        initial_state = create_initial_state(args)
        final_state = loop.run_until_complete(asyncio.wait_for(run_main_workflow(initial_state), timeout=600))
        if final_state.get("scenario_results"):
            failures = [r for r in final_state["scenario_results"] if not r.get("passed", True)]
            exit_code = 0 if not failures else 1
        else:
            exit_code = 1
    except asyncio.TimeoutError:
        logger.error("Workflow timed out")
        exit_code = 3
    except Exception as e:
        logger.exception("CRITICAL WORKFLOW FAILURE: %s", str(e))
        exit_code = 4
    finally:
        loop.close()
        logger.info("Execution completed at: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        sys.exit(exit_code)