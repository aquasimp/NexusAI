"""Initialize all Python package __init__.py files, exports, and backward-compatible aliases."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "backend" / "nexus"

def write(rel_path: str, content: str):
    p = BASE / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {p}")

def main():
    # nexus/__init__.py
    write("__init__.py", '"""NEXUS AI - Autonomous Incident Intelligence Platform."""\n__version__ = "1.0.0"\n')

    # nexus/config/__init__.py
    write("config/__init__.py", 'from .settings import settings, Settings\n\n__all__ = ["settings", "Settings"]\n')

    # nexus/config.py (compatibility)
    write("config.py", '"""Compatibility alias for nexus.config.settings."""\nfrom .config.settings import settings, Settings\n\n__all__ = ["settings", "Settings"]\n')

    # nexus/core/__init__.py
    write("core/__init__.py", '"""Core cross-cutting concerns: logging, exceptions, dependencies."""\nfrom .logging import get_logger, logger\nfrom .exceptions import NexusError, SimulationError, IncidentNotFoundError, PolicyViolationError, RemediationError\n')

    # nexus/core/logging.py
    write("core/logging.py", '''"""Centralized structured logger for NEXUS AI."""
import logging
import sys

def get_logger(name: str = "nexus") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = get_logger()
''')

    # nexus/core/exceptions.py
    write("core/exceptions.py", '''"""Domain exceptions for NEXUS AI."""

class NexusError(Exception):
    """Base exception for all NEXUS AI domain errors."""
    pass

class SimulationError(NexusError):
    """Raised when simulation invariants or ticks encounter an error."""
    pass

class IncidentNotFoundError(NexusError):
    """Raised when requested incident ID does not exist."""
    pass

class PolicyViolationError(NexusError):
    """Raised when an action violates safety or gating policies."""
    pass

class RemediationError(NexusError):
    """Raised when remediation action fails or verification fails."""
    pass
''')

    # nexus/realtime/__init__.py
    write("realtime/__init__.py", 'from .hub import hub, Hub\n\n__all__ = ["hub", "Hub"]\n')

    # nexus/hub.py (compatibility)
    write("hub.py", '"""Compatibility alias for nexus.realtime.hub."""\nfrom .realtime.hub import hub, Hub\n\n__all__ = ["hub", "Hub"]\n')

    # nexus/persistence/__init__.py
    write("persistence/__init__.py", 'from .store import *\n')

    # nexus/store.py (compatibility)
    write("store.py", '"""Compatibility alias for nexus.persistence.store."""\nfrom .persistence.store import *\n')

    # nexus/simulation/__init__.py
    write("simulation/__init__.py", '''from .topology import (
    SERVICES, EDGES, METRICS, ENTRYPOINT, REVENUE_PER_REQ,
    ServiceSpec, eval_order, callers_of, dependents_transitive, EVAL_ORDER
)
from .engine import Engine, Fault, Deploy
from .scenarios import SCENARIOS, Scenario, arm
from .logs import synthesize, to_dict, LogLine

__all__ = [
    "SERVICES", "EDGES", "METRICS", "ENTRYPOINT", "REVENUE_PER_REQ", "ServiceSpec",
    "eval_order", "callers_of", "dependents_transitive", "EVAL_ORDER",
    "Engine", "Fault", "Deploy",
    "SCENARIOS", "Scenario", "arm",
    "synthesize", "to_dict", "LogLine"
]
''')


    # nexus/ml/__init__.py
    write("ml/__init__.py", '''from .detector import Detector
from .rca_model import RCARanker, CLASSES, build_pipeline, save, load
from .correlate import localize
from .features import extract, FEATURE_NAMES, N_FEATURES
from .changepoint import cusum

__all__ = [
    "Detector", "RCARanker", "CLASSES", "build_pipeline", "save", "load",
    "localize", "extract", "FEATURE_NAMES", "N_FEATURES", "cusum"
]
''')

    # nexus/rag/__init__.py
    write("rag/__init__.py", 'from .store import KB, KnowledgeBase, Chunk\n\n__all__ = ["KB", "KnowledgeBase", "Chunk"]\n')

    # nexus/agent/__init__.py
    write("agent/__init__.py", 'from .orchestrator import Investigation, STAGES\nfrom .llm import LLMClient\nfrom . import tools, impact, remediation\n\n__all__ = ["Investigation", "STAGES", "LLMClient", "tools", "impact", "remediation"]\n')

    # nexus/evaluation/__init__.py
    write("evaluation/__init__.py", 'from . import benchmark, metrics, runner\n\n__all__ = ["benchmark", "metrics", "runner"]\n')


    # nexus/api/__init__.py
    write("api/__init__.py", 'from .routes import router\n\n__all__ = ["router"]\n')

    print("All package inits and compatibility wrappers created.")

if __name__ == "__main__":
    main()
