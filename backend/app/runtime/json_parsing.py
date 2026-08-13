import re

from pydantic import BaseModel, ValidationError

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```\s*$", re.MULTILINE)


class JsonOutputError(ValueError):
    """Raised when model output can't be parsed into the expected model.
    Carries the raw text for debugging / feeding back into a retry prompt."""

    def __init__(self, message: str, raw_text: str) -> None:
        super().__init__(message)
        self.raw_text = raw_text


def parse_model_json[T: BaseModel](text: str, model: type[T]) -> T:
    """Parses LLM output into a Pydantic model, tolerating markdown code
    fences and surrounding prose (falls back to the outermost {...} slice)."""
    stripped = _FENCE_RE.sub("", text).strip()

    try:
        return model.model_validate_json(stripped)
    except ValidationError:
        pass

    # Some models wrap the JSON in prose despite instructions - try the
    # outermost object literal before giving up.
    start, end = stripped.find("{"), stripped.rfind("}")
    if start != -1 and end > start:
        try:
            return model.model_validate_json(stripped[start : end + 1])
        except ValidationError as exc:
            raise JsonOutputError(
                f"Output doesn't match {model.__name__}: {exc}", raw_text=text
            ) from exc

    raise JsonOutputError(f"No JSON object found in output for {model.__name__}", raw_text=text)
