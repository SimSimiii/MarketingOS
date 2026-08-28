from typing import Any


class CampaignError(Exception):
    """Base for every error the campaign pipeline raises. Carries structured
    debugging context, same convention as app.runtime.exceptions."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r}, details={self.details!r})"


class StrategyError(CampaignError):
    """Raised when no usable campaign brief could be produced - there is
    nothing for the craft phase to execute."""


class CraftError(CampaignError):
    """Raised when an email could not be produced in a sendable form, after
    the writer was given its own errors back."""
