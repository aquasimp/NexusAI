"""Benchmark execution script for NEXUS AI."""
import argparse
import sys
from pathlib import Path

# Ensure backend is on sys.path
BASE = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BASE))

from nexus.evaluation.runner import main

if __name__ == "__main__":
    main()
