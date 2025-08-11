import os
from typing import Dict, Any


class FrameworkInitAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print("🔧 FrameworkInitAgent: Starting framework initialization...")
        
        orchestrator = state["orchestrator"]
        print(f"🔧 FrameworkInitAgent: Output directory: {orchestrator.output_dir}")
        print(f"🔧 FrameworkInitAgent: Config path: {orchestrator.config_path}")
        
        # Check if output directory exists
        if not os.path.exists(orchestrator.output_dir):
            print(f"🔧 FrameworkInitAgent: Output directory does not exist, will create: {orchestrator.output_dir}")
        else:
            print(f"🔧 FrameworkInitAgent: Output directory exists: {orchestrator.output_dir}")
        
        details = await orchestrator.detect_existing_framework()
        print(f"🔧 FrameworkInitAgent: Detection result: {details}")

        if not details.get("valid"):
            print("🔧 FrameworkInitAgent: Framework not valid, initializing...")
            ok, info = await orchestrator.initialize_framework()
            print(f"🔧 FrameworkInitAgent: Initialization result: {ok}, {info}")
            details.update(info)
            state["framework_initialized"] = ok
        else:
            print("🔧 FrameworkInitAgent: Framework already valid, skipping initialization")
            state["framework_initialized"] = True

        state["framework_details"] = details
        print(f"🔧 FrameworkInitAgent: Final state: {state['framework_initialized']}")
        return state