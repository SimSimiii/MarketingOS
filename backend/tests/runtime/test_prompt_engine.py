from pathlib import Path

import pytest

from app.runtime.exceptions import PromptNotFoundError, PromptValidationError
from app.runtime.prompt_engine import PromptEngine


def test_render_injects_variables(prompts_dir: Path):
    engine = PromptEngine(prompts_dir)
    result = engine.render(
        "dummy", {"agent_name": "Dummy Agent", "version": "0.1.0", "message": "world"}
    )
    assert "Dummy Agent" in result
    assert "0.1.0" in result
    assert "world" in result


def test_render_missing_template_raises_not_found(prompts_dir: Path):
    engine = PromptEngine(prompts_dir)
    with pytest.raises(PromptNotFoundError):
        engine.render("does_not_exist", {})


def test_render_missing_variables_raises_validation_error(prompts_dir: Path):
    engine = PromptEngine(prompts_dir)
    with pytest.raises(PromptValidationError) as exc_info:
        engine.render("dummy", {"agent_name": "Dummy Agent"})

    assert "version" in exc_info.value.details["missing_variables"]
    assert "message" in exc_info.value.details["missing_variables"]


def test_source_is_cached_after_first_read(prompts_dir: Path):
    engine = PromptEngine(prompts_dir)
    variables = {"agent_name": "A", "version": "1", "message": "hi"}
    engine.render("dummy", variables)

    # Mutate the file on disk - cached render should be unaffected.
    (prompts_dir / "dummy.md").write_text("changed", encoding="utf-8")
    result = engine.render("dummy", variables)
    assert "changed" not in result
