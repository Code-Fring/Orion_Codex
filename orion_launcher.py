#!/usr/bin/env python3
"""Orion Codex - Standalone executable launcher.

This script can be compiled to a standalone executable using PyInstaller:
    pyinstaller --onefile --name orion orion_launcher.py
"""

import os
import sys
import subprocess
from pathlib import Path


def find_python():
    """Find Python executable."""
    # Try common Python commands
    for cmd in ["python3", "python", "py"]:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                return cmd
        except FileNotFoundError:
            continue
    return None


def main():
    # Get the directory where this executable/script is located
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_dir = Path(sys.executable).parent
    else:
        # Running as script
        base_dir = Path(__file__).parent
    
    backend_path = base_dir / "backend"
    
    # If backend not found next to executable, try to find it
    if not backend_path.exists():
        # Check if we're in a pip package installation
        import site
        for site_dir in site.getsitepackages():
            potential = Path(site_dir) / "orion_codex" / "backend"
            if potential.exists():
                backend_path = potential
                break
    
    # Add backend to Python path
    if backend_path.exists():
        sys.path.insert(0, str(backend_path))
    else:
        print("Error: Could not find Orion Codex backend", file=sys.stderr)
        print(f"Searched: {backend_path}", file=sys.stderr)
        sys.exit(1)
    
    # Run the CLI
    try:
        from backend.cli.main import app
        app()
    except ImportError as e:
        print(f"Error importing Orion Codex: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running Orion Codex: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()