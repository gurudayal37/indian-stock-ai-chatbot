#!/usr/bin/env python3
"""
Wrapper script to run smart syncer with the correct Python interpreter
"""

import sys
import os

# Use Anaconda Python path
ANACONDA_PYTHON = "/opt/anaconda3/bin/python"

def main():
    """Run the smart syncer with the correct Python"""
    script_path = os.path.join(os.path.dirname(__file__), "smart_yahoo_syncer.py")
    
    if not os.path.exists(script_path):
        print(f"❌ Error: {script_path} not found")
        sys.exit(1)
    
    if not os.path.exists(ANACONDA_PYTHON):
        print(f"❌ Error: Anaconda Python not found at {ANACONDA_PYTHON}")
        print("Please update the ANACONDA_PYTHON path in this script")
        sys.exit(1)
    
    print(f"🚀 Running smart syncer with: {ANACONDA_PYTHON}")
    print(f"📁 Script: {script_path}")
    print("=" * 60)
    
    # Execute the script
    os.execv(ANACONDA_PYTHON, [ANACONDA_PYTHON, script_path])

if __name__ == "__main__":
    main()
