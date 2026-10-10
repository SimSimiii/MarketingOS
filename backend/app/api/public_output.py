"""Remove internal vendor accounting from customer-facing event payloads."""

from typing import Any

from app.core.config import get_settings

_PRIVATE_KEYS = frozenset({
    "model", "model_overrides", "input_tokens", "output_tokens",
    "cache_creation_input_tokens", "cache_read_input_tokens", "cache_read_tokens",
    "total_input_tokens", "total_output_tokens", "total_cache_read_tokens",
    "cost_usd", "estimated_cost_usd", "observed_cost_per_email",
    "prompt_chars", "response_chars",
})

_CALL_MESSAGES = {
    "model_call_started": "Preparing this step…",
    "model_call_finished": "Step completed",
    "model_call_retried": "Retrying this step…",
}


def public_message(event_type: str | None, message: str) -> str:
    if get_settings().credit_billing_enabled:
        return _CALL_MESSAGES.get(event_type or "", message)
    return message


def public_output(value: Any) -> Any:
    """Preserve internal diagnostics while prepaid customers see product progress."""
    if not get_settings().credit_billing_enabled:
        return value
    if isinstance(value, dict):
        cleaned = {key: public_output(item) for key, item in value.items()
                if key not in _PRIVATE_KEYS}
        if "message" in cleaned and isinstance(cleaned["message"], str):
            cleaned["message"] = public_message(value.get("type"), cleaned["message"])
        return cleaned
    if isinstance(value, list):
        return [public_output(item) for item in value]
    return value
