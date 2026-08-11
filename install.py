#!/usr/bin/env python3
"""Orion Codex - Installation script.

This script installs Orion Codex globally so you can run 'orion' from any terminal.

Usage:
    python install.py [--user] [--prefix PREFIX]

Options:
    --user      Install for current user only (default)
    --prefix    Install to custom prefix directory
    --help      Show this help
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path


def get_install_paths(user_install=True, prefix=None):
    """Get installation paths."""
    if prefix:
        bin_dir = Path(prefix) / "bin"
        lib_dir = Path(prefix) / "lib" / "orion-codex"
    elif user_install:
        # User installation
        if sys.platform == "win32":
            bin_dir = Path(os.environ.get("APPDATA", "")) / "OrionCodex" / "bin"
            lib_dir = Path(os.environ.get("APPDATA", "")) / "OrionCodex" / "lib"
        else:
            bin_dir = Path.home() / ".local" / "bin"
            lib_dir = Path.home() / ".local" / "lib" / "orion-codex"
    else:
        # System installation
        bin_dir = Path("/usr/local/bin")
        lib_dir = Path("/usr/local/lib/orion-codex")
    
    return bin_dir, lib_dir


def install_orion(source_dir, bin_dir, lib_dir, user_install=True):
    """Install Orion Codex."""
    source_dir = Path(source_dir).resolve()
    bin_dir = Path(bin_dir).resolve()
    lib_dir = Path(lib_dir).resolve()
    
    # Create directories
    bin_dir.mkdir(parents=True, exist_ok=True)
    lib_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Installing Orion Codex...")
    print(f"  Source: {source_dir}")
    print(f"  Bin: {bin_dir}")
    print(f"  Lib: {lib_dir}")
    
    # Copy backend to lib directory
    backend_src = source_dir / "backend"
    backend_dst = lib_dir / "backend"
    
    if backend_dst.exists():
        shutil.rmtree(backend_dst)
    
    shutil.copytree(backend_src, backend_dst)
    print(f"  Copied backend to {backend_dst}")
    
    # Copy frontend if exists
    frontend_src = source_dir / "frontend"
    frontend_dst = lib_dir / "frontend"
    if frontend_src.exists():
        if frontend_dst.exists():
            shutil.rmtree(frontend_dst)
        shutil.copytree(frontend_src, frontend_dst)
        print(f"  Copied frontend to {frontend_dst}")
    
    # Create launcher scripts
    if sys.platform == "win32":
        # Windows batch file
        bat_content = f'''@echo off
REM Orion Codex launcher
set BACKEND_PATH={lib_dir}\\backend
set PYTHONPATH=%BACKEND_PATH%;%PYTHONPATH%
python -m backend.cli.main %*
'''
        (bin_dir / "orion.bat").write_text(bat_content)
        
        # PowerShell script
        ps1_content = f'''<# 
.SYNOPSIS
    Orion Codex - Terminal-first AI Coding Agent launcher for PowerShell
#>

param(
    [string[]]$Arguments = @()
)

$BackendPath = "{lib_dir}\\backend"
$env:PYTHONPATH = "$BackendPath;$env:PYTHONPATH"

python -m backend.cli.main @Arguments
'''
        (bin_dir / "orion.ps1").write_text(ps1_content)
        
        # Python launcher
        py_content = f'''#!/usr/bin/env python3
"""Orion Codex launcher."""
import sys
import os
sys.path.insert(0, r"{lib_dir}\\backend")
from backend.cli.main import app
app()
'''
        (bin_dir / "orion.py").write_text(py_content)
        
        print(f"  Created orion.bat, orion.ps1, orion.py in {bin_dir}")
    else:
        # Unix shell script
        sh_content = f'''#!/bin/bash
# Orion Codex launcher
export BACKEND_PATH="{lib_dir}/backend"
export PYTHONPATH="$BACKEND_PATH:$PYTHONPATH"
exec python3 -m backend.cli.main "$@"
'''
        launcher_path = bin_dir / "orion"
        launcher_path.write_text(sh_content)
        launcher_path.chmod(0o755)
        
        # Python launcher
        py_content = f'''#!/usr/bin/env python3
"""Orion Codex launcher."""
import sys
sys.path.insert(0, "{lib_dir}/backend")
from backend.cli.main import app
app()
'''
        (bin_dir / "orion.py").write_text(py_content)
        (bin_dir / "orion.py").chmod(0o755)
        
        print(f"  Created orion, orion.py in {bin_dir}")
    
    # Create config directory
    config_dir = Path.home() / ".orion"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy example config if it doesn't exist
    example_env = source_dir / ".env.example"
    if example_env.exists():
        target_env = config_dir / ".env"
        if not target_env.exists():
            shutil.copy2(example_env, target_env)
            print(f"  Created config at {target_env}")
    
    print("\nInstallation complete!")
    print(f"\nAdd {bin_dir} to your PATH to run 'orion' from anywhere.")
    
    if sys.platform != "win32":
        shell_rc = Path.home() / ".bashrc"
        if not shell_rc.exists():
            shell_rc = Path.home() / ".zshrc"
        if shell_rc.exists():
            print(f"\nAdd this to your {shell_rc}:")
            print(f'  export PATH="{bin_dir}:$PATH"')
    else:
        print(f"\nAdd {bin_dir} to your system PATH environment variable.")
    
    print("\nThen run 'orion --help' to get started!")


def main():
    parser = argparse.ArgumentParser(description="Install Orion Codex globally")
    parser.add_argument("--user", action="store_true", default=True,
                        help="Install for current user (default)")
    parser.add_argument("--system", action="store_false", dest="user",
                        help="Install system-wide (requires sudo)")
    parser.add_argument("--prefix", type=str, help="Custom installation prefix")
    parser.add_argument("--source", type=str, default=".",
                        help="Source directory (default: current)")
    
    args = parser.parse_args()
    
    source_dir = Path(args.source).resolve()
    if not (source_dir / "backend").exists():
        print(f"Error: Source directory {source_dir} does not contain backend/", file=sys.stderr)
        sys.exit(1)
    
    bin_dir, lib_dir = get_install_paths(user_install=args.user, prefix=args.prefix)
    
    try:
        install_orion(source_dir, bin_dir, lib_dir, args.user)
    except PermissionError:
        print("Error: Permission denied. Try running with --user or use sudo for system install.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()