"""Core cross-cutting concerns: logging, exceptions, dependencies."""
from .logging import get_logger, logger
from .exceptions import NexusError, SimulationError, IncidentNotFoundError, PolicyViolationError, RemediationError
