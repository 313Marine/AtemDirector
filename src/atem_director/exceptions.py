"""Custom exception hierarchy for ATEM Director."""


class ATEMDirectorException(Exception):
    """Base exception for all ATEM Director errors."""
    pass


class ConfigurationError(ATEMDirectorException):
    """Configuration is invalid or missing."""
    pass


class ValidationError(ATEMDirectorException):
    """Input validation failed."""
    pass


class ConnectionError(ATEMDirectorException):
    """ATEM device connection failed."""
    pass


class ATEMCommandError(ATEMDirectorException):
    """Command sent to ATEM device failed."""
    pass


class StateTransitionError(ATEMDirectorException):
    """Invalid state transition attempted."""
    pass


class PersistenceError(ATEMDirectorException):
    """Database operation failed."""
    pass


class NoEligibleInputsError(ATEMDirectorException):
    """No inputs available for switching."""
    pass


class OperationFailed(ATEMDirectorException):
    """Operation could not complete."""
    pass
