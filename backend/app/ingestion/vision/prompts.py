"""Fixed instruction strings for each VisionProvider operation. Plain string
constants, not templates - none of these need variable injection, so there's
no reason to route them through app.runtime's PromptEngine (which would
couple this package to the agent runtime). Every instruction demands strict
JSON matching the corresponding Pydantic model and forbids summarization or
subjective judgment - only factual, structural extraction."""

_JSON_ONLY = "Respond with ONLY a single JSON object, no prose, no markdown code fences."

ANALYZE_IMAGE_PROMPT = f"""Describe exactly what is visibly present in this image: objects, text,
people, layout - factually, with no summarization, opinion, or marketing judgment.
{_JSON_ONLY} Schema: {{"description": string, "confidence": number between 0 and 1}}"""

EXTRACT_TEXT_PROMPT = f"""Read every piece of text visible in this image, verbatim, in reading
order. Do not paraphrase or summarize. If you can tell the language, name it (e.g. "en", "fr").
{_JSON_ONLY} Schema: {{"text": string, "detected_language": string or null}}"""

DESCRIBE_LAYOUT_PROMPT = f"""Identify the structural regions visible in this image (e.g. header,
navigation, hero, sidebar, footer, body). List only regions that are actually present.
{_JSON_ONLY} Schema: {{"regions": [string], "details": object}}"""

IDENTIFY_OBJECTS_PROMPT = f"""List the distinct physical objects, UI elements (buttons, forms,
icons), and products visible in this image. Factual labels only, no interpretation.
{_JSON_ONLY} Schema: {{"objects": [string]}}"""

IDENTIFY_BRANDING_PROMPT = f"""Identify any logos or brand names visibly present in this image.
Only report what is actually visible - do not guess a brand from style alone.
{_JSON_ONLY} Schema: {{"logos": [string], "brand_names": [string]}}"""

IDENTIFY_COLORS_PROMPT = f"""Identify the dominant colors in this image as hex codes, ordered from
most to least dominant.
{_JSON_ONLY} Schema: {{"colors": [string]}}"""
