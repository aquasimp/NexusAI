"""Launch both Backend (FastAPI) and Frontend (Next.js) concurrently for local development."""
import subprocess
import sys
import os
import signal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
WEB = ROOT / "web"

VENV_PY = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
VENV_UVICORN = BACKEND / ".venv" / ("Scripts/uvicorn.exe" if os.name == "nt" else "bin/uvicorn")

def main():
    print("=" * 60)
    print(" Starting NEXUS AI Development Environment")
    print(f" Backend: http://localhost:8000 (API & SSE)")
    print(f" Web UI:  http://localhost:3000")
    print("=" * 60)

    # Launch Backend
    backend_cmd = [str(VENV_UVICORN), "nexus.main:app", "--reload", "--port", "8000"]
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(BACKEND))

    # Launch Frontend
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    web_cmd = [npm_cmd, "run", "dev"]
    web_proc = subprocess.Popen(web_cmd, cwd=str(WEB))

    def shutdown(sig, frame):
        print("\nShutting down NEXUS AI servers...")
        backend_proc.terminate()
        web_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    backend_proc.wait()
    web_proc.wait()

if __name__ == "__main__":
    main()
