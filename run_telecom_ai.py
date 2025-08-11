#!/usr/bin/env python3
"""
Telecom AI LangGraph Launcher
Automatically handles dependencies and launches the main application.
"""

import sys
import os
import subprocess
from pathlib import Path


def main():
    """Main launcher function."""
    print("🚀 Telecom AI LangGraph Launcher")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("telecom_ai_langgraph.py").exists():
        print("❌ Error: telecom_ai_langgraph.py not found in current directory")
        print("Please run this script from the project root directory")
        sys.exit(1)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Check if requirements.txt exists
    if Path("requirements.txt").exists():
        print("✓ requirements.txt found")
    else:
        print("⚠️  requirements.txt not found")
    
    # Check if dependency_installer.py exists
    if Path("dependency_installer.py").exists():
        print("✓ dependency_installer.py found")
        
        # Run dependency installer first
        print("\n🔧 Running dependency installer...")
        try:
            result = subprocess.run([sys.executable, "dependency_installer.py"], check=True)
            print("✓ Dependencies verified/installed")
        except subprocess.CalledProcessError:
            print("❌ Dependency installation failed")
            sys.exit(1)
    else:
        print("⚠️  dependency_installer.py not found, will attempt direct execution")
    
    # Launch the main application
    print("\n🚀 Launching Telecom AI LangGraph...")
    print("=" * 40)
    
    try:
        # Import and run the main module
        from telecom_ai_langgraph import main as telecom_main
        
        # Parse command line arguments
        import argparse
        parser = argparse.ArgumentParser(description="Resilient Telecom Test Automation")
        parser.add_argument(
            "user_story",
            nargs="?",
            default="As a telecom user, I want to verify mobile data usage API",
            help="User story describing test scenario",
        )
        parser.add_argument("--config", default="telecom_config.json")
        parser.add_argument("--max-healing", type=int, default=3)
        parser.add_argument("--disable-auto-healing", action="store_true")
        parser.add_argument("--output-dir", default="./telecom_api_bdd")
        parser.add_argument("--verbose", "-v", action="store_true")
        
        args = parser.parse_args()
        
        # Create initial state and run
        initial_state = telecom_main.create_initial_state(args)
        import asyncio
        asyncio.run(telecom_main.run_main_workflow(initial_state))
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This usually means dependencies are missing.")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Runtime error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
