"""Deterministic, non-LLM text analysis over SEC filing text.

Used by BusinessModelAnalyzer to (a) select a relevant slice of a long
filing section for a specific prompt instead of always sending the first
N characters, and (b) scan for cost pass-through/escalation language for a
specific business driver without relying on the LLM to notice it.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')


def split_sentences(text: str) -> List[str]:
    """Lightweight sentence splitter: splits on a sentence-ending
    punctuation mark followed by whitespace and a capital letter. Misses
    some abbreviation edge cases (e.g. "Mr. Smith") but is good enough for
    keyword/proximity matching, where an occasional over-split sentence
    just means the adjacent-sentence window below is already doing its job.
    """
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def select_keyword_context(text: str, keywords: List[str], cap: int = 5000, context_sentences: int = 1) -> Tuple[str, Dict[str, Any]]:
    """Select sentences (plus `context_sentences` of surrounding context)
    that mention any of `keywords`, in order of appearance, up to `cap`
    characters. Falls back to the first `cap` characters if nothing matches,
    so a caller always gets a usable (if less targeted) slice.

    Returns (slice_text, meta) where meta records which path was taken, for
    debugging/grounding-transparency purposes (per-prompt slice logging).
    """
    if not text:
        return '', {'method': 'empty_source'}

    sentences = split_sentences(text)
    if not sentences:
        return text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'no_sentences'}

    pattern = re.compile('|'.join(re.escape(k) for k in keywords if k), re.IGNORECASE)
    matched_indices = sorted({
        j
        for i, s in enumerate(sentences) if pattern.search(s)
        for j in range(max(0, i - context_sentences), min(len(sentences), i + context_sentences + 1))
    })

    if not matched_indices:
        return text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'no_keyword_matches', 'keywords': keywords}

    selected = []
    total_len = 0
    for idx in matched_indices:
        sentence = sentences[idx]
        if total_len + len(sentence) > cap:
            break
        selected.append(sentence)
        total_len += len(sentence) + 1

    slice_text = ' '.join(selected)
    return slice_text, {
        'method': 'keyword_sentences',
        'keywords': keywords,
        'sentences_matched': len(matched_indices),
        'sentences_used': len(selected),
        'chars_used': len(slice_text),
    }


# Mechanism keywords are deliberately generic (no commodity name baked in,
# e.g. no "fuel") - confirmed directly on KEX that the same filing uses this
# language for both fuel ("fuel escalation clauses") and unrelated cost types
# ("annual escalators for labor and the producer price index"), so a
# commodity-specific keyword list would both miss cases and not generalize
# to other companies/industries.
_MECHANISM_PATTERNS = [
    r'escalat\w*',
    r'pass[- ]through',
    r'surcharge',
    r'cost\s+recovery',
    r'recover\w*\s+(?:changes\s+in\s+)?(?:specific\s+)?costs',
    r'indexed\s+to',
    r'adjust\w*\s+for\s+changes\s+in',
]
_MECHANISM_RE = re.compile('|'.join(_MECHANISM_PATTERNS), re.IGNORECASE)

# Required in the SAME sentence as the mechanism keyword - excludes generic
# risk-factor language like "costs may escalate due to inflation" which
# mentions the mechanism word but isn't describing an actual contractual
# pass-through arrangement.
_CONTRACT_CONTEXT_RE = re.compile(r'\b(contracts?|agreements?|provisions?|clauses?|rates?)\b', re.IGNORECASE)

_STRENGTH_PATTERNS = [
    ('full', re.compile(r'\b(substantially all|all of our contracts|fully)\b', re.IGNORECASE)),
    ('partial', re.compile(r'\b(may or may not|partially|a portion of|a number of|some)\b', re.IGNORECASE)),
    ('none', re.compile(r'\b(do not have|unable to pass|cannot recover)\b', re.IGNORECASE)),
]

_LAG_RE = re.compile(r'\b(\d+\s*(?:to\s*\d+\s*)?days?|monthly|quarterly|annual(?:ly)?)\b', re.IGNORECASE)


def scan_pass_through(full_text: str, driver_terms: List[str]) -> Optional[Dict[str, Any]]:
    """Deterministic (no LLM) scan for cost pass-through/escalation
    language tied to a specific driver, over the full filing text.

    A match requires: a generic mechanism keyword, a driver-specific term
    (from `driver_terms` - the driver's own name plus 2-4 synonyms) in the
    same or an adjacent sentence, and contract-context wording in the same
    sentence as the mechanism keyword (excludes risk-factor boilerplate).

    Returns None if no qualifying match is found - absence of evidence is
    not asserted as evidence of no pass-through, it just means this driver
    gets no pass-through annotation at all.
    """
    if not full_text or not driver_terms:
        return None

    sentences = split_sentences(full_text)
    if not sentences:
        return None

    # A driver term this generic matches almost any contract-adjustment
    # sentence regardless of actual subject - confirmed directly: the LLM
    # gave "Interest rates" the synonym "rate" (one of its own suggested
    # 2-4 synonyms), which then matched KEX's unrelated fuel escalation
    # clause ("The rate may or may not include escalation provisions...")
    # purely because it contains the word "rate". Filtered out here rather
    # than trusting every LLM-supplied synonym to be specific enough.
    _GENERIC_TERMS = {'rate', 'rates', 'cost', 'costs', 'price', 'prices', 'fee', 'fees', 'charge', 'charges'}
    usable_terms = [t for t in driver_terms if t and t.strip().lower() not in _GENERIC_TERMS]
    if not usable_terms:
        return None

    term_pattern = re.compile('|'.join(re.escape(t) for t in usable_terms), re.IGNORECASE)

    matches = []
    for i, sentence in enumerate(sentences):
        if not _MECHANISM_RE.search(sentence):
            continue
        if not _CONTRACT_CONTEXT_RE.search(sentence):
            continue
        window = sentences[max(0, i - 1):i + 2]
        if not term_pattern.search(' '.join(window)):
            continue
        matches.append(sentence)

    if not matches:
        return None

    # Grade strength/lag from the same sentences shown as evidence, not the
    # full (possibly longer) match list - otherwise the lag or strength can
    # come from a sentence the reader never sees.
    evidence = matches[:3]
    combined = ' '.join(evidence)
    strength = 'partial'
    for label, pattern in _STRENGTH_PATTERNS:
        if pattern.search(combined):
            strength = label
            break

    lag_match = _LAG_RE.search(combined)
    return {
        'strength': strength,
        'lag': lag_match.group(0) if lag_match else None,
        'evidence': evidence,
    }
