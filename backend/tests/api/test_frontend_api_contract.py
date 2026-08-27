"""Every path the frontend calls must be one the backend actually serves.

`frontend/src/lib/api-client.ts` hardcodes all 48 of them and
`frontend/src/lib/types.ts` mirrors the Pydantic schemas by hand, so renaming a
route breaks the UI with a 404 that no backend test can see and no frontend
check looks for - there is no CI and no frontend test runner. This reads the
paths back out of the client and licenses each against the OpenAPI schema,
which is the same move as the evidence gate: a claim made in one artifact,
checked against the only source allowed to license it.

Free and deterministic. `app.openapi()` spends no model call.
"""

import re
from pathlib import Path

import pytest

from app.main import app

API_CLIENT = (
    Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "api-client.ts"
)

# Every request goes through `${API_URL}${path}`, and API_URL carries the mount.
API_PREFIX = "/api"
API_URL_TOKEN = "${API_URL}"


def _collapse_interpolations(template: str) -> str:
    """Replace each `${...}` with `{}`, counting braces so a nested one survives.

    A regex cannot do this: `${includeArchived ? "?x=1" : ""}` contains braces
    and quotes of its own.
    """
    out: list[str] = []
    index = 0
    while index < len(template):
        if template.startswith("${", index):
            depth, cursor = 1, index + 2
            while cursor < len(template) and depth:
                if template[cursor] == "{":
                    depth += 1
                elif template[cursor] == "}":
                    depth -= 1
                cursor += 1
            out.append("{}")
            index = cursor
        else:
            out.append(template[index])
            index += 1
    return "".join(out)


def _to_openapi_path(template: str) -> str:
    """Normalise one TypeScript path template to its OpenAPI shape.

    The one rule that separates a path parameter from an appended query string:
    a path parameter is always preceded by `/`, a query append never is. That
    holds for every form in the client - a literal `?limit=${n}`, a ternary
    `${archived ? "?..." : ""}`, and a prebuilt `${suffix}` alike - so the
    normalisation is exact rather than a guess, which is what lets this test
    block. A heuristic here would fail a correct change.
    """
    template = template.removeprefix(API_URL_TOKEN)
    path = _collapse_interpolations(template).split("?", 1)[0]
    if path.endswith("{}") and not path.endswith("/{}"):
        path = path[:-2]
    return path.rstrip("/") or "/"


def _paths_the_frontend_calls() -> set[str]:
    source = API_CLIENT.read_text(encoding="utf-8")

    # request<T>(`...`) and request<T>("...") - templates and plain strings both.
    calls = re.findall(
        r'(?:request|upload)<[^>]*>\(\s*(?:`([^`]*)`|"([^"]*)")', source
    )
    templates = [backtick or quoted for backtick, quoted in calls]
    # The SSE stream and the CSV export build their URL directly, bypassing the
    # two helpers above; they are still endpoints the UI depends on.
    templates += re.findall(r"`(\$\{API_URL\}[^`]*)`", source)

    # `${API_URL}${path}` inside the helpers themselves normalises to "/": it is
    # the caller's path, not an endpoint. A real one has a literal segment.
    return {
        path for path in map(_to_openapi_path, templates) if path.startswith("/") and path != "/"
    }


def _paths_the_backend_serves() -> set[str]:
    return {re.sub(r"\{[^}]*\}", "{}", path) for path in app.openapi()["paths"]}


def test_the_api_client_reads_back_as_paths_at_all() -> None:
    """Guard the guard.

    The check below passes vacuously if the extraction ever silently matches
    nothing - a renamed helper, a reformatted call. Pin the count low enough
    that ordinary edits do not trip it and high enough that a broken regex does.
    """
    found = _paths_the_frontend_calls()
    assert len(found) > 30, (
        f"only {len(found)} paths parsed out of {API_CLIENT.name}; the extraction "
        "has probably stopped matching rather than the client having shrunk"
    )


def test_every_path_the_frontend_calls_is_served_by_the_backend() -> None:
    served = _paths_the_backend_serves()
    unserved = sorted(
        path for path in _paths_the_frontend_calls() if API_PREFIX + path not in served
    )
    assert not unserved, (
        "the frontend calls paths this backend does not serve:\n  "
        + "\n  ".join(API_PREFIX + path for path in unserved)
        + "\n\nEither the route was renamed and api-client.ts was not, or the "
        "client is calling something that never existed. Served paths:\n  "
        + "\n  ".join(sorted(served))
    )


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("/brands/${id}", "/brands/{}"),
        ("/campaigns", "/campaigns"),
        # Query appended three different ways - none of them a path parameter.
        ('/campaigns${includeArchived ? "?include_archived=true" : ""}', "/campaigns"),
        ("/executions/${executionId}/logs${suffix}", "/executions/{}/logs"),
        ("/logs?limit=${limit}", "/logs"),
        ("/knowledge/base?${query}", "/knowledge/base"),
        # ...and a path parameter that is genuinely one, in final position.
        ("/market/${brandId}/rivals/${rivalId}", "/market/{}/rivals/{}"),
        ("${API_URL}/executions/${executionId}/stream", "/executions/{}/stream"),
    ],
)
def test_a_query_append_is_not_mistaken_for_a_path_parameter(
    template: str, expected: str
) -> None:
    assert _to_openapi_path(template) == expected
