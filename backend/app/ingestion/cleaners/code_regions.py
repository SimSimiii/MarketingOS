"""Protect literal Markdown code while cleaning surrounding prose."""

import re
from collections.abc import Callable

_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_INLINE = re.compile(r"(?<!`)(`+)(?!`)[^\n]*?(?<!`)\1(?!`)")


def preserve_code(text: str, clean: Callable[[str], str]) -> str:
    blocks: list[tuple[int, int]] = []
    start: int | None = None
    fence = ""
    offset = 0
    for line in text.splitlines(keepends=True):
        if start is None:
            if match := _OPEN.match(line):
                start, fence = offset, match.group(1)
        elif re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*\r?\n?", line):
            blocks.append((start, offset + len(line)))
            start = None
        offset += len(line)
    if start is not None:
        blocks.append((start, len(text)))
    spans: list[tuple[int, int]] = []
    previous = 0
    for first, last in [*blocks, (len(text), len(text))]:
        spans.extend((previous + match.start(), previous + match.end())
                     for match in _INLINE.finditer(text[previous:first]))
        if first != last:
            spans.append((first, last))
        previous = last
    prefix = "\0CODE_REGION_"
    while prefix in text:
        prefix += "_"
    parts: list[str] = []
    replacements: list[tuple[str, str]] = []
    previous = 0
    for index, (first, last) in enumerate(spans):
        marker = f"{prefix}{index}\0"
        parts.extend((text[previous:first], marker))
        replacements.append((marker, text[first:last]))
        previous = last
    parts.append(text[previous:])
    result = clean("".join(parts))
    for marker, literal in replacements:
        result = result.replace(marker, literal)
    return result
