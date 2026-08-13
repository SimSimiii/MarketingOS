from typing import Any


class ModelRuntimeError(Exception):
    """Base for every error the model runtime raises. Carries structured
    debugging context."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r}, details={self.details!r})"


class PromptNotFoundError(ModelRuntimeError):
    """Raised when a requested prompt template file does not exist."""


class PromptValidationError(ModelRuntimeError):
    """Raised when a prompt template references variables that were not supplied."""


class ProviderError(ModelRuntimeError):
    """Raised when the underlying AI provider call fails.

    Typed here so one transient blip - the CLI failing to start, a dropped
    connection - fails a single call the pipeline can account for, instead of
    escaping as a vendor-specific exception nobody catches and taking a
    campaign with minutes of work in it down with it.
    """


class OutputValidationError(ModelRuntimeError):
    """Raised when a role's answer cannot be parsed into the model it promised."""
