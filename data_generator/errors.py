"""Custom exceptions for data generation."""


class DataGenerationError(Exception):
    """Base class for data-generation failures."""


class ConfigError(DataGenerationError):
    """Raised when a configuration file is invalid."""


class PlacementError(DataGenerationError):
    """Raised when an entity cannot be placed in the grid."""


class PathfindingError(DataGenerationError):
    """Raised when canonical travel costs cannot be computed."""


class GenerationError(DataGenerationError):
    """Raised when a full instance cannot be generated."""


class ValidationError(DataGenerationError):
    """Raised when an assembled instance fails validation."""
