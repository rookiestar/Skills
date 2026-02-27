#!/usr/bin/env python3
"""
Release Script - Manages file visibility across local repo, remote repo, and npm package.

This script handles three layers:
1. Local repo - All tracked files (managed by .gitignore)
2. Remote repo - Public files only
3. npm package - Minimal user-facing files

Usage:
    python3 scripts/release.py --check        # Show file distribution
    python3 scripts/release.py --sync-remote  # Sync to remote (dry-run)
    python3 scripts/release.py --npm-pack     # Create npm tarball
"""

import argparse
import subprocess
import json
from pathlib import Path
from typing import Set

# Files/directories to EXCLUDE from remote repo (not publicly visible)
REMOTE_EXCLUDE = {
    "tests/",
    "package.json",
    "package-lock.json",
    "bin/",
    "scripts/setup.py",
    ".gitignore",
    ".gitattributes",
    ".npmignore",
    "*.egg-info/",
    ".pytest_cache/",
    "__pycache__/",
    ".coverage",
    "htmlcov/",
    ".tox/",
    ".nox/",
    ".claude/",
    "*.pyc",
    "*.pyo",
    "*.tgz",
}

# Files/directories to EXCLUDE from npm package (in addition to REMOTE_EXCLUDE)
# npm package should be minimal - only what users need to run
NPM_EXCLUDE = REMOTE_EXCLUDE | {
    "CLAUDE.md",           # Development guide for Claude AI
    "docs/",               # Internal documentation
    "examples/",           # Sample files (not needed for runtime)
    "references/",         # Reference materials
    "*.md",                # All markdown except README.md
}

# Files that MUST be included in npm package
NPM_INCLUDE = {
    "README.md",           # Keep README for npm display
    "package.json",        # Required for npm
    "requirements.txt",    # Python dependencies
    "scripts/",            # All scripts (excluding setup.py)
    "templates/",          # Prompt templates
    "SKILL.md",           # Skill documentation
}


def get_tracked_files() -> Set[str]:
    """Get all files tracked by git."""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return set(result.stdout.strip().split("\n"))


def should_exclude(path: str, exclude_patterns: Set[str]) -> bool:
    """Check if a path should be excluded based on patterns."""
    for pattern in exclude_patterns:
        if pattern.endswith("/"):
            if path.startswith(pattern) or "/" + pattern in path:
                return True
        elif pattern.startswith("*."):
            if path.endswith(pattern[1:]):
                return True
        else:
            if path == pattern or path.startswith(pattern + "/"):
                return True
    return False


def categorize_files():
    """Categorize files into local, remote, and npm groups."""
    tracked = get_tracked_files()

    local_only = set()
    remote_files = set()
    npm_files = set()

    for file in tracked:
        # Skip empty strings
        if not file:
            continue

        # Check if in remote exclude list
        if should_exclude(file, REMOTE_EXCLUDE):
            local_only.add(file)
        else:
            remote_files.add(file)

        # Check if should be in npm package
        if should_exclude(file, NPM_EXCLUDE):
            # Check if explicitly included
            included = False
            for inc_pattern in NPM_INCLUDE:
                if inc_pattern.endswith("/"):
                    if file.startswith(inc_pattern):
                        included = True
                        break
                elif file == inc_pattern:
                    included = True
                    break

            if included:
                npm_files.add(file)
        else:
            npm_files.add(file)

    return local_only, remote_files, npm_files


def show_distribution():
    """Show file distribution across three layers."""
    local_only, remote_files, npm_files = categorize_files()

    print("=" * 60)
    print("FILE DISTRIBUTION ACROSS THREE LAYERS")
    print("=" * 60)

    print(f"\n📦 LOCAL REPO ONLY ({len(local_only)} files)")
    print("-" * 40)
    for f in sorted(local_only):
        print(f"  {f}")

    print(f"\n🌐 REMOTE REPO (public, {len(remote_files)} files)")
    print("-" * 40)
    for f in sorted(remote_files):
        print(f"  {f}")

    print(f"\n📦 NPM PACKAGE ({len(npm_files)} files)")
    print("-" * 40)
    for f in sorted(npm_files):
        print(f"  {f}")

    print("\n" + "=" * 60)
    print(f"SUMMARY: Local={len(local_only) + len(remote_files)} | Remote={len(remote_files)} | npm={len(npm_files)}")
    print("=" * 60)


def create_gitattributes():
    """Create .gitattributes with export-ignore for local-only files."""
    eng_lang_tutor_dir = Path(__file__).parent.parent
    gitattributes_path = eng_lang_tutor_dir / ".gitattributes"

    # Patterns to exclude from git archive (remote export)
    export_ignore_patterns = [
        "tests/",
        ".pytest_cache/",
        "*.pyc",
        "*.pyo",
        ".coverage",
        "htmlcov/",
        ".tox/",
        ".nox/",
        ".claude/",
        "*.egg-info/",
        "*.tgz",
    ]

    content = "# Files to exclude from git archive export\n"
    content += "# These files are tracked locally but not exported to remote archives\n\n"

    for pattern in export_ignore_patterns:
        content += f"{pattern} export-ignore\n"

    gitattributes_path.write_text(content)
    print(f"✓ Created {gitattributes_path}")
    print("\nNote: This affects 'git archive' only.")
    print("For selective push to remote, consider using a separate public branch.")


def npm_pack():
    """Create npm tarball with proper file filtering."""
    eng_lang_tutor_dir = Path(__file__).parent.parent

    # Update package.json files field for npm
    package_json_path = eng_lang_tutor_dir / "package.json"

    with open(package_json_path) as f:
        package = json.load(f)

    # Set files field to include only what we want
    package["files"] = [
        "scripts/",
        "templates/",
        "SKILL.md",
        "README.md",
        "requirements.txt",
    ]

    # Remove tests from npm package
    if "!tests/**" in package.get("files", []):
        pass  # Already excluded

    print("npm pack would include:")
    print(json.dumps(package.get("files", []), indent=2))

    print("\nRun the following to create npm package:")
    print(f"  cd {eng_lang_tutor_dir} && npm pack")


def main():
    parser = argparse.ArgumentParser(
        description="Manage file visibility across local repo, remote repo, and npm package"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Show file distribution across three layers"
    )
    parser.add_argument(
        "--create-gitattributes",
        action="store_true",
        help="Create .gitattributes with export-ignore rules"
    )
    parser.add_argument(
        "--npm-pack",
        action="store_true",
        help="Show npm pack configuration"
    )

    args = parser.parse_args()

    if args.check:
        show_distribution()
    elif args.create_gitattributes:
        create_gitattributes()
    elif args.npm_pack:
        npm_pack()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
