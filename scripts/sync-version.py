#!/usr/bin/env python3
"""Sync version from pyproject.toml to Chrome extension manifest.json.

Usage:
    python scripts/sync-version.py          # Write manifest.json
    python scripts/sync-version.py --check   # Check mismatch only, don't write; exit code 1 means mismatch
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PYPROJECT = REPO / "pyproject.toml"
MANIFEST = REPO / "src" / "cdp_bridge" / "tmwd_cdp_bridge" / "manifest.json"


def read_version_pyproject(path: Path) -> str:
    text = path.read_text()
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        print("ERROR: version field not found in pyproject.toml", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def read_version_manifest(path: Path) -> str:
    data = json.loads(path.read_text())
    return data["version"]


def write_manifest_version(path: Path, version: str) -> None:
    data = json.loads(path.read_text())
    data["version"] = version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"  manifest.json version -> {version}")


def write_pyproject_version(path: Path, version: str) -> None:
    text = path.read_text()
    text = re.sub(r'^version\s*=\s*"[^"]+"', f'version = "{version}"', text, count=1, flags=re.MULTILINE)
    path.write_text(text)
    print(f"  pyproject.toml version -> {version}")


def main() -> None:
    # Prefer --publish-version:
    #   Read version from CLI argument, write to both pyproject.toml and manifest.json
    publish_idx = None
    try:
        publish_idx = sys.argv.index("--publish-version")
    except ValueError:
        pass

    if publish_idx is not None:
        version = sys.argv[publish_idx + 1]
        write_pyproject_version(PYPROJECT, version)
        write_manifest_version(MANIFEST, version)
        return

    check_only = "--check" in sys.argv

    pyproject_ver = read_version_pyproject(PYPROJECT)
    manifest_ver = read_version_manifest(MANIFEST)

    if pyproject_ver == manifest_ver:
        print(f"OK: versions match ({pyproject_ver})")
        sys.exit(0)

    print(f"pyproject.toml:    {pyproject_ver}")
    print(f"manifest.json:    {manifest_ver}")

    if check_only:
        print("mismatch, exit code 1")
        sys.exit(1)

    write_manifest_version(MANIFEST, pyproject_ver)


if __name__ == "__main__":
    main()
