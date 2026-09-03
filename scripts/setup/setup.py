"""Cross-platform one-command developer setup for NEXUS AI."""
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
WEB = ROOT / "web"
VENV = BACKEND / ".venv"

def run(cmd, cwd=ROOT):
    print(f"\n--> Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, cwd=str(cwd), shell=isinstance(cmd, str))
    if res.returncode != 0:
        print(f"ERROR: Command failed with exit code {res.returncode}")
        sys.exit(res.returncode)

def main():
    print("=" * 60)
    print(" NEXUS AI Developer Setup")
    print("=" * 60)

    # 1. Python virtualenv
    if not VENV.exists():
        print("Creating backend virtual environment...")
        run([sys.executable, "-m", "venv", str(VENV)])

    pip = str(VENV / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip"))
    run([pip, "install", "--upgrade", "pip"])
    run([pip, "install", "-r", str(BACKEND / "requirements.txt")])
    run([pip, "install", "-r", str(BACKEND / "requirements-dev.txt")])
    run([pip, "install", "-e", str(BACKEND)])

    # 2. Package inits
    init_script = ROOT / "scripts" / "setup" / "init_packages.py"
    if init_script.exists():
        py = str(VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        run([py, str(init_script)])

    # 3. Web npm install
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    run([npm_cmd, "install"], cwd=WEB)

    print("\n" + "=" * 60)
    print(" ✓ NEXUS AI Setup Complete!")
    print(" Run 'make dev' or 'python scripts/development/run_dev.py' to start.")
    print("=" * 60)

if __name__ == "__main__":
    main()
