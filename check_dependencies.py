#!/usr/bin/env python
"""
Dependency checker for Gomoku ML Coach
Run this to verify all required packages are installed correctly.
"""

import sys
from importlib import import_module

# List of required packages
REQUIRED_PACKAGES = {
    'pandas': 'pandas',
    'numpy': 'numpy',
    'xgboost': 'xgboost',
    'sklearn': 'scikit-learn',
    'dateutil': 'python-dateutil',
    'tkinter': 'tkinter (built-in)',
}

def check_package(package_name, display_name):
    """Check if a package is installed."""
    try:
        import_module(package_name)
        print(f"✓ {display_name:20} - OK")
        return True
    except ImportError:
        print(f"✗ {display_name:20} - MISSING")
        return False

def main():
    print("=" * 60)
    print("Gomoku ML Coach - Dependency Checker")
    print("=" * 60)
    print()
    
    all_ok = True
    for package_name, display_name in REQUIRED_PACKAGES.items():
        if not check_package(package_name, display_name):
            all_ok = False
    
    print()
    print("=" * 60)
    
    if all_ok:
        print("✓ All dependencies are installed!")
        print("You can now run: python main.py")
        return 0
    else:
        print("✗ Some dependencies are missing.")
        print()
        print("To install missing packages, run:")
        print("  pip install -r requirements.txt")
        print()
        print("Or upgrade pip first:")
        print("  python -m pip install --upgrade pip")
        print("  pip install -r requirements.txt --force-reinstall")
        return 1

if __name__ == "__main__":
    sys.exit(main())
