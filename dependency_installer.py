#!/usr/bin/env python3
"""
Dependency Installer for Telecom AI LangGraph Application
Automatically installs missing dependencies when running the application.
"""

import subprocess
import sys
import importlib
import os
from typing import List, Dict, Tuple


class DependencyInstaller:
    def __init__(self):
        self.required_packages = {
            'langgraph': 'langgraph==0.2.35',
            'langchain': 'langchain==0.2.12',
            'langchain_core': 'langchain-core==0.3.25',
            'langchain_community': 'langchain-community==0.3.25',
            'behave': 'behave==1.2.6',
            'requests': 'requests==2.32.3',
            'jsonpath_ng': 'jsonpath-ng==1.6.0',
            'pydantic': 'pydantic==2.8.2',
            'aiofiles': 'aiofiles==24.1.0',
            'python_dotenv': 'python-dotenv==1.0.1',
            'typing_extensions': 'typing-extensions==4.12.2'
        }
        
        self.optional_packages = {
            'pytest': 'pytest==8.2.2',
            'pytest_asyncio': 'pytest-asyncio==0.24.0'
        }

    def check_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed."""
        try:
            importlib.import_module(package_name)
            return True
        except ImportError:
            return False

    def get_missing_packages(self) -> List[str]:
        """Get list of missing required packages."""
        missing = []
        for package, requirement in self.required_packages.items():
            if not self.check_package_installed(package):
                missing.append(requirement)
        return missing

    def install_package(self, package: str) -> bool:
        """Install a single package using pip."""
        try:
            print(f"Installing {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✓ Successfully installed {package}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}: {e}")
            print(f"Error output: {e.stderr}")
            return False

    def install_missing_packages(self) -> bool:
        """Install all missing required packages."""
        missing = self.get_missing_packages()
        
        if not missing:
            print("✓ All required packages are already installed!")
            return True
        
        print(f"Found {len(missing)} missing packages. Installing...")
        print("=" * 50)
        
        failed_installations = []
        for package in missing:
            if not self.install_package(package):
                failed_installations.append(package)
        
        if failed_installations:
            print("\n" + "=" * 50)
            print("✗ Failed to install the following packages:")
            for package in failed_installations:
                print(f"  - {package}")
            print("\nPlease install them manually using:")
            print(f"pip install {' '.join(failed_installations)}")
            return False
        
        print("\n" + "=" * 50)
        print("✓ All required packages installed successfully!")
        return True

    def verify_installation(self) -> bool:
        """Verify that all required packages can be imported."""
        print("\nVerifying package installation...")
        failed_imports = []
        
        for package in self.required_packages.keys():
            if not self.check_package_installed(package):
                failed_imports.append(package)
        
        if failed_imports:
            print("✗ The following packages still cannot be imported:")
            for package in failed_imports:
                print(f"  - {package}")
            return False
        
        print("✓ All packages can be imported successfully!")
        return True

    def run(self) -> bool:
        """Main method to run the dependency installer."""
        print("🔧 Telecom AI LangGraph Dependency Installer")
        print("=" * 50)
        
        # Check if we're in a virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("✓ Virtual environment detected")
        else:
            print("⚠️  No virtual environment detected. Consider using one for better dependency management.")
        
        print()
        
        # Install missing packages
        if not self.install_missing_packages():
            return False
        
        # Verify installation
        if not self.verify_installation():
            return False
        
        print("\n🎉 All dependencies are ready! You can now run:")
        print("python telecom_ai_langgraph.py")
        return True


def main():
    """Main entry point."""
    installer = DependencyInstaller()
    success = installer.run()
    
    if not success:
        print("\n❌ Dependency installation failed. Please check the errors above.")
        sys.exit(1)
    
    print("\n✅ Ready to run your application!")


if __name__ == "__main__":
    main()
