"""Pytest test configuration and fixtures for NEXUS AI."""
import pytest
from nexus.simulation.engine import Engine
from nexus.rag.store import KB

@pytest.fixture
def engine():
    """Provides a fresh simulation engine instance."""
    return Engine(seed=42)

@pytest.fixture
def knowledge_base():
    """Provides access to the initialized runbook knowledge base."""
    return KB
