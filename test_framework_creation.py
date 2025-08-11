#!/usr/bin/env python3
"""
Test script to verify framework creation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telecom_test_orchestrator import TelecomTestOrchestrator


async def test_framework_creation():
    """Test the framework creation process."""
    print("🧪 Testing Framework Creation")
    print("=" * 40)
    
    # Test output directory
    test_output_dir = "./test_framework_output"
    config_path = "./telecom_config.json"
    
    print(f"Output directory: {os.path.abspath(test_output_dir)}")
    print(f"Config path: {os.path.abspath(config_path)}")
    print()
    
    # Create orchestrator
    orchestrator = TelecomTestOrchestrator(
        output_dir=test_output_dir,
        config_path=config_path,
        debug=True
    )
    
    # Test framework detection
    print("1. Testing framework detection...")
    detection_result = await orchestrator.detect_existing_framework()
    print(f"Detection result: {detection_result}")
    print()
    
    # Test framework initialization
    print("2. Testing framework initialization...")
    init_result = await orchestrator.initialize_framework()
    print(f"Initialization result: {init_result}")
    print()
    
    # Verify framework creation
    print("3. Verifying framework creation...")
    verification_result = await orchestrator.detect_existing_framework()
    print(f"Verification result: {verification_result}")
    print()
    
    # List created files and directories
    print("4. Listing created files and directories:")
    if os.path.exists(test_output_dir):
        for root, dirs, files in os.walk(test_output_dir):
            level = root.replace(test_output_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
    else:
        print("❌ Output directory was not created!")
    
    print()
    print("5. Framework creation test completed!")
    
    # Cleanup
    if os.path.exists(test_output_dir):
        import shutil
        shutil.rmtree(test_output_dir)
        print("✓ Cleaned up test directory")


if __name__ == "__main__":
    asyncio.run(test_framework_creation())
