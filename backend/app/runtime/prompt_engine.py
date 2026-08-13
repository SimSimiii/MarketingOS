from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined, meta

from app.runtime.exceptions import PromptNotFoundError, PromptValidationError


class PromptEngine:
    """Loads prompt templates from disk and renders them with variable
    injection. Prompts are never hardcoded in Python - every agent's
    system_prompt is a template name resolved against `prompts_dir`."""

    def __init__(self, prompts_dir: Path) -> None:
        self._prompts_dir = prompts_dir
        self._env = Environment(undefined=StrictUndefined, keep_trailing_newline=True)
        self._source_cache: dict[str, str] = {}

    def render(self, template_name: str, variables: dict[str, Any]) -> str:
        source = self._load_source(template_name)

        required = meta.find_undeclared_variables(self._env.parse(source))
        missing = sorted(required - variables.keys())
        if missing:
            raise PromptValidationError(
                f"Prompt '{template_name}' is missing variables: {', '.join(missing)}",
                template_name=template_name,
                missing_variables=missing,
            )

        template = self._env.from_string(source)
        return template.render(**variables)

    def _load_source(self, template_name: str) -> str:
        if template_name in self._source_cache:
            return self._source_cache[template_name]

        path = self._prompts_dir / f"{template_name}.md"
        if not path.is_file():
            raise PromptNotFoundError(
                f"Prompt template '{template_name}' not found at {path}",
                template_name=template_name,
                path=str(path),
            )

        source = path.read_text(encoding="utf-8")
        self._source_cache[template_name] = source
        return source


@lru_cache(maxsize=4)
def get_prompt_engine(prompts_dir: Path) -> PromptEngine:
    """Process-wide engine for a prompts directory.

    The engine caches template sources on the instance, so building a new one
    per campaign meant re-reading every prompt file from disk on every run.
    Templates are read-only at runtime; edits require a restart, same as any
    other code change.
    """
    return PromptEngine(prompts_dir)
