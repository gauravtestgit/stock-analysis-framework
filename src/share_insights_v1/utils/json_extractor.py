from typing import Optional
import json
import re


def extract_json_from_llm_response(response: str) -> Optional[str]:
    """Extract a JSON object from an LLM's text response.

    Several analyzers asked an LLM for structured JSON and each hand-rolled
    their own extraction with a single-level regex fallback
    (r'\\{[^{}]*(?:\\{[^{}]*\\}[^{}]*)*\\}') for responses that don't wrap the
    JSON in a markdown code fence. That regex only correctly matches one flat
    level of nesting - confirmed broken on a real response containing a list
    of multiple nested dicts (an industry analysis's "growth_drivers": [...]),
    where it silently matched and returned just one list item's sub-object
    instead of the full structure, with no error raised anywhere.

    This uses json.JSONDecoder.raw_decode for the non-fenced fallback instead
    of a regex, so correctness matches whatever the json module itself
    considers valid JSON at any nesting depth, rather than a hand-rolled
    guess. Tries, in order: a ```json fenced block, a plain ``` fenced block
    whose content parses as JSON, then a decoder-driven scan of the raw text.
    Returns None (not the raw response) when nothing parseable is found, so
    callers get a clean, checkable failure instead of a string that will
    raise downstream with no clue why.

    Deliberately object-only (starts from '{', never '['): every prompt these
    analyzers use asks for a JSON object at the root, never a top-level array,
    and scanning for '[' too caused a real regression - an LLM response's own
    prose containing something bracket-like before the real JSON (a citation
    like "[1]", which is itself valid-but-wrong JSON: a one-element array of
    the number 1) got matched first, long before reaching the actual object.

    Only attempts the FIRST '{' found, never falls through to a later one.
    Confirmed real case: a verbose prompt's response got token-limit
    truncated mid-structure (cut off partway through, no closing brace, a
    field missing entirely) - the intended top-level object, so raw_decode
    on it correctly fails. Scanning onward from there used to "succeed" by
    landing on the first complete nested sub-object instead (one item of a
    "growth_drivers" list), silently returning a small, wrong-shaped result
    that looks like a clean success to the caller. There is no way to
    recover data the LLM never generated, so failing cleanly (None, which
    callers already treat as "use the fallback") is correct here - a small
    fragment with the wrong keys is worse than an honest failure.
    """
    match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        if _is_valid_json(candidate):
            return candidate

    match = re.search(r'```\s*\n(.*?)\n```', response, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        if candidate.startswith('{') and _is_valid_json(candidate):
            return candidate

    start = response.find('{')
    if start != -1:
        try:
            decoder = json.JSONDecoder()
            _, end = decoder.raw_decode(response, start)
            return response[start:end]
        except json.JSONDecodeError:
            pass

    return None


def _is_valid_json(candidate: str) -> bool:
    try:
        json.loads(candidate)
        return True
    except json.JSONDecodeError:
        return False
