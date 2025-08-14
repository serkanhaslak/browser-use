#!/usr/bin/env python3
"""
Main entry point for browser-use Railway deployment.
This file helps Railpack detect the project as Python.
"""

import os
import sys
import subprocess

def main():
    """Main entry point that delegates to the startup script."""
    # Make startup script executable
    startup_script = os.path.join(os.path.dirname(__file__), 'startup.sh')
    if os.path.exists(startup_script):
        os.chmod(startup_script, 0o755)
        # Execute the startup script
        subprocess.run([startup_script], check=True)
    else:
        print("Error: startup.sh not found")
        sys.exit(1)

if __name__ == "__main__":
    main()