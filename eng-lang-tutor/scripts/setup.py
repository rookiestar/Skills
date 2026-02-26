#!/usr/bin/env python3
"""
Setup script for eng-lang-tutor skill.
Installs Python dependencies with support for virtual environments.

Usage:
    eng-lang-tutor-setup              # Install dependencies
    eng-lang-tutor-setup --venv       # Create venv and install
    eng-lang-tutor-setup --check      # Check dependencies only
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def get_package_dir() -> Path:
    """Get the package directory containing requirements.txt."""
    # When installed via npm, the script is symlinked in node_modules/.bin/
    # We need to find the actual package directory
    script_path = Path(__file__).resolve()

    # Check if we're in a typical npm global install location
    if "node_modules" in str(script_path):
        # Navigate to the package root
        parts = script_path.parts
        for i, part in enumerate(parts):
            if part == "node_modules":
                # Find the package directory (usually @scope/package or just package)
                remaining = parts[i + 1 :]
                if remaining and remaining[0].startswith("@"):
                    # Scoped package: @rookiestar/eng-lang-tutor
                    pkg_dir = Path(*parts[: i + 3])
                else:
                    # Unscoped package
                    pkg_dir = Path(*parts[: i + 2])
                return pkg_dir

    # Fallback: assume script is in scripts/ directory
    return script_path.parent.parent


def check_dependencies() -> tuple[bool, list[str]]:
    """Check if all required dependencies are installed."""
    missing = []
    required = ["websocket", "certifi", "aiohttp", "edge_tts"]

    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    return len(missing) == 0, missing


def install_dependencies(
    requirements_path: Path, venv_path: Path | None = None, user: bool = False
) -> bool:
    """Install dependencies from requirements.txt."""
    if not requirements_path.exists():
        print(f"Error: requirements.txt not found at {requirements_path}")
        return False

    pip_cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)]

    if venv_path:
        pip_cmd = [str(venv_path / "bin" / "pip"), "install", "-r", str(requirements_path)]
    elif user:
        pip_cmd.append("--user")

    try:
        print(f"Installing dependencies from {requirements_path}...")
        subprocess.run(pip_cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False


def create_venv(venv_path: Path) -> bool:
    """Create a virtual environment."""
    try:
        print(f"Creating virtual environment at {venv_path}...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Setup script for eng-lang-tutor skill"
    )
    parser.add_argument(
        "--venv",
        metavar="PATH",
        nargs="?",
        const="~/.venvs/eng-lang-tutor",
        help="Create a virtual environment and install dependencies (default: ~/.venvs/eng-lang-tutor)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if dependencies are installed without installing",
    )
    parser.add_argument(
        "--user",
        action="store_true",
        help="Install dependencies to user directory (use with --break-system-packages if needed)",
    )

    args = parser.parse_args()

    pkg_dir = get_package_dir()
    requirements_path = pkg_dir / "requirements.txt"

    # Check mode
    if args.check:
        ok, missing = check_dependencies()
        if ok:
            print("All dependencies are installed.")
            sys.exit(0)
        else:
            print(f"Missing dependencies: {', '.join(missing)}")
            print("Run this script without --check to install them.")
            sys.exit(1)

    # Venv mode
    if args.venv:
        venv_path = Path(args.venv).expanduser().resolve()

        if not (venv_path / "bin" / "python").exists():
            if not create_venv(venv_path):
                sys.exit(1)

        if install_dependencies(requirements_path, venv_path=venv_path):
            print(f"\nSuccess! Virtual environment created at {venv_path}")
            print(f"To activate it, run: source {venv_path}/bin/activate")
            sys.exit(0)
        else:
            sys.exit(1)

    # Direct install mode
    if install_dependencies(requirements_path, user=args.user):
        print("\nDependencies installed successfully!")
        sys.exit(0)
    else:
        print("\nInstallation failed. Try one of these alternatives:")
        print("  1. Create a virtual environment: eng-lang-tutor-setup --venv")
        print("  2. Install to user directory: eng-lang-tutor-setup --user")
        print("  3. If you understand the risks: pip install -r requirements.txt --break-system-packages")
        sys.exit(1)


if __name__ == "__main__":
    main()
