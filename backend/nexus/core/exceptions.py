"""Domain exceptions for NEXUS AI."""

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
