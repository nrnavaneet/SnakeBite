#!/usr/bin/env python3
"""Cross-platform runtime setup: venv + pip install + optional flutter pub get.

Does not build ML assets unless SETUP_BUILD_ASSETS=1.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    venv = root / ".venv"
    py_exe = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    print("SnakeBiteRx runtime setup")
    print(f"Repo: {root}")

    if not venv.exists():
        print("Creating .venv ...")
        run([sys.executable, "-m", "venv", str(venv)])
    else:
        print("Reusing existing .venv")

    print("Upgrading pip ...")
    run([str(py_exe), "-m", "pip", "install", "--upgrade", "pip"])
    print("Installing Python dependencies ...")
    run([str(py_exe), "-m", "pip", "install", "-r", str(root / "requirements.txt")])

    if os.getenv("SETUP_BUILD_ASSETS", "0") == "1":
        print("Building ML assets (SETUP_BUILD_ASSETS=1) ...")
        run([str(py_exe), "-m", "ml.build_assets"], cwd=root)
    else:
        print("Skipping ML asset build (SETUP_BUILD_ASSETS=0).")
        print("Run `make assets` later if needed.")

    flutter = shutil.which("flutter")
    if flutter:
        print("Running flutter pub get ...")
        run([flutter, "pub", "get"], cwd=root / "mobile" / "snakebite_rx")
    else:
        print("Flutter not found in PATH; skipping pub get.")

    print("Setup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
