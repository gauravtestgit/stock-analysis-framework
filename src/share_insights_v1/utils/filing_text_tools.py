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
    that mention any of `keywords`, up to `cap` characters, prioritizing the
    most SPECIFIC keyword each sentence matches when the budget can't fit
    everything. Falls back to the first `cap` characters if nothing matches,
    so a caller always gets a usable (if less targeted) slice.

    Confirmed directly why specificity-based priority (not just document
    order) matters: given both a generic single word ("fleet", "capacity")
    and a specific multi-word phrase ("contracts of affreightment", "term
    contract") as keywords, the generic ones matched many early, irrelevant
    sentences and consumed the entire budget before reaching the specific
    phrase's real matches later in the document - the caller received a
    slice about rental equipment instead of the contract-structure
    discussion it actually asked for. Longer keyword = more specific =
    filled first; the final slice is still presented in natural reading
    order once selected, so the LLM reads coherent prose, not priority-sorted
    fragments.

    Returns (slice_text, meta) where meta records which path was taken, for
    debugging/grounding-transparency purposes (per-prompt slice logging).
    """
    if not text:
        return '', {'method': 'empty_source'}

    sentences = split_sentences(text)
    if not sentences:
        return text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'no_sentences'}

    sorted_keywords = sorted({k for k in keywords if k}, key=len, reverse=True)
    if not sorted_keywords:
        return text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'no_keywords'}

    # Longest keyword each sentence matches = that sentence's priority.
    sentence_priority: Dict[int, int] = {}
    for i, s in enumerate(sentences):
        s_lower = s.lower()
        for kw in sorted_keywords:  # already longest-first
            if kw.lower() in s_lower:
                sentence_priority[i] = len(kw)
                break

    if not sentence_priority:
        return text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'no_keyword_matches', 'keywords': keywords}

    # Fill the budget highest-priority match first. Among sentences tied on
    # keyword-length priority, a sentence containing a digit is preferred
    # before falling back to document order - confirmed directly why this
    # matters on PRDO: "Title IV" appears 125 times across the filing, and
    # with document-order as the only tiebreak, the first ~9 matches
    # (faculty bios, Dept. of Education reorg news) consumed the whole
    # budget before reaching the one sentence far later that actually
    # states the required 90/10 Title IV revenue percentage. A qualitative
    # mention rarely carries a number; the actual disclosure (a percentage,
    # dollar figure, or count) almost always does, so this is a general
    # retrieval improvement, not a PRDO-specific keyword tweak.
    has_digit = lambda i: any(c.isdigit() for c in sentences[i])
    ranked = sorted(sentence_priority.keys(), key=lambda i: (-sentence_priority[i], 0 if has_digit(i) else 1, i))

    selected_indices: set = set()
    total_len = 0
    for i in ranked:
        window = range(max(0, i - context_sentences), min(len(sentences), i + context_sentences + 1))
        new_indices = [j for j in window if j not in selected_indices]
        added_len = sum(len(sentences[j]) + 1 for j in new_indices)
        if total_len + added_len > cap:
            continue  # this match doesn't fit - a smaller, lower-priority one still might
        selected_indices.update(new_indices)
        total_len += added_len

    selected_in_order = sorted(selected_indices)
    slice_text = ' '.join(sentences[i] for i in selected_in_order)[:cap]
    return slice_text, {
        'method': 'keyword_sentences',
        'keywords': keywords,
        'sentences_matched': len(sentence_priority),
        'sentences_used': len(selected_in_order),
        'chars_used': len(slice_text),
    }


_STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'per', 'via', 'its', 'own',
    'does', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'has', 'have', 'had',
    'what', 'which', 'who', 'how', 'when', 'where', 'why', 'of', 'to', 'in', 'on',
    'as', 'at', 'by', 'or', 'not', 'no', 'if', 'than', 'then', 'so', 'but', 'also', 'any',
    'quote', 'quoted', 'filing', 'state', 'states', 'statement', 'question', 'answer',
    'company', 'companys', 'disclose', 'disclosed',
}
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]+")


def _content_words(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text or '') if len(w) > 2 and w.lower() not in _STOPWORDS]


def select_ranked_windows(
    text: str, question_text: str, keywords: List[str], cap: int = 2000, max_windows: int = 3,
    context_sentences: int = 1,
) -> List[Tuple[str, Dict[str, Any]]]:
    """Rank every sentence by relevance to the QUESTION ITSELF (not just
    where_to_look keyword presence), and return up to `max_windows`
    non-overlapping candidate slices in rank order - the caller tries
    window 1 first and only moves to window 2+ if window 1 doesn't yield a
    verified answer, instead of ever sending just one fixed slice.

    Why this exists: select_keyword_context above is itself fully
    deterministic, but confirmed directly that a question's real answer
    can still land outside the single window it builds when a where_to_look
    keyword is very common (PRDO: "regulator" alone matched 73 sentences,
    "government program" matched 109, with only a handful fitting the
    cap) - whichever few sentences happen to win the keyword-length/digit
    tiebreak are not guaranteed to be the ones that actually answer the
    question, and there was no second attempt at a different slice if the
    first one came up empty, which an LLM call used to silently read as
    "not disclosed" even when the real sentence was in the document, just
    not in that one slice.

    The ranking here is a lightweight relevance heuristic, not real BM25
    (no corpus-wide document-frequency table to compute a true IDF from) -
    it scores each sentence by word overlap with the question's own content
    words, overlap with the archetype's where_to_look keywords (weighted
    higher, since those are known-relevant terms), and a small bonus for
    containing a digit (an actual disclosure is usually a number). Ranking
    is by (score, sentence index) only - no sets involved in the ordering
    itself, so it's deterministic across runs for the same input, unlike
    relying on Python's per-process string-hash randomization anywhere in
    the sort key.
    """
    if not text:
        return [('', {'method': 'empty_source'})]
    sentences = split_sentences(text)
    if not sentences:
        return [(text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'no_sentences'})]

    question_words = _content_words(question_text)
    keyword_words: List[str] = []
    for kw in keywords:
        keyword_words.extend(_content_words(kw))
    if not question_words and not keyword_words:
        return [(text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'no_keywords'})]

    # Real IDF (inverse sentence-frequency), computed once over this
    # filing's own sentences - confirmed directly why plain word/keyword
    # overlap isn't enough on its own: a where_to_look term like "Title IV"
    # repeats in ~125 sentences of mostly generic regulatory boilerplate,
    # so sentences dense with several SUCH common terms scored far higher
    # than the one sentence that actually states the required disclosure
    # ("...preliminary calculations... remain in compliance with the
    # 90/10 threshold...", which only contains "90/10" once and no other
    # repeated keyword) - that sentence ranked 162nd despite being the
    # right one. IDF down-weights a term by how common it already is
    # across THIS filing's sentences, so a rare, specific term like
    # "90/10" (appearing once) counts for far more than a common one like
    # "Title IV" - the same principle BM25 uses, without needing a
    # corpus-wide document-frequency table (there's only one document here).
    import math
    sentence_word_sets = [set(_content_words(s)) for s in sentences]
    doc_freq: Dict[str, int] = {}
    for sw in sentence_word_sets:
        for w in sw:
            doc_freq[w] = doc_freq.get(w, 0) + 1
    n_sentences = len(sentences)

    def idf(word: str) -> float:
        return math.log((n_sentences + 1) / (doc_freq.get(word, 0) + 1)) + 1.0

    keywords_lower = [kw.lower() for kw in keywords if kw]
    # Document frequency for a keyword PHRASE (substring match, not just
    # its tokenized words) - same IDF treatment: "90/10" appearing in 2
    # sentences scores far higher per-hit than "Title IV" appearing in 125.
    keyword_doc_freq = {kw: sum(1 for s in sentences if kw in s.lower()) for kw in keywords_lower}

    scored = []
    for i, s in enumerate(sentences):
        s_lower = s.lower()
        s_words = sentence_word_sets[i]
        matching_kws = [kw for kw in keywords_lower if kw in s_lower]
        q_overlap = sum(idf(w) for w in question_words if w in s_words)
        kw_overlap = sum(idf(w) * 2.0 for w in keyword_words if w in s_words)
        kw_substring_hits = sum(
            (math.log((n_sentences + 1) / (keyword_doc_freq.get(kw, 0) + 1)) + 1.0) * 2.0
            for kw in matching_kws
        )
        has_digit = any(c.isdigit() for c in s)
        # A sentence that pairs a digit with a RARE keyword match (one that
        # appears in only a handful of sentences across the whole filing)
        # is the strongest possible signal of being the actual disclosure,
        # as opposed to one of many generic boilerplate mentions of a common
        # keyword - confirmed directly this needed to be a much bigger,
        # keyword-rarity-scaled bonus than a flat "has a digit" one: with
        # only a flat bonus, a sentence repeating a COMMON keyword ("Title
        # IV", matching ~100 sentences) several different ways still
        # outscored the one sentence with a genuinely rare keyword match
        # ("90/10", matching 1 sentence) plus the real percentage figure.
        rarity_digit_bonus = 0.0
        if has_digit and matching_kws:
            rarest_df = min(keyword_doc_freq.get(kw, n_sentences) for kw in matching_kws)
            rarity_digit_bonus = 40.0 / (rarest_df + 1)
        digit_bonus = 3.0 if has_digit else 0.0
        scored.append((i, q_overlap + kw_overlap + kw_substring_hits + digit_bonus + rarity_digit_bonus))

    ranked_indices = [i for i, score in sorted(scored, key=lambda pair: (-pair[1], pair[0])) if score > 0]
    if not ranked_indices:
        return [(text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'no_keyword_matches', 'keywords': keywords})]

    windows: List[Tuple[str, Dict[str, Any]]] = []
    used: set = set()
    pos = 0
    for window_num in range(max_windows):
        selected: set = set()
        total_len = 0
        added_any = False
        while pos < len(ranked_indices):
            i = ranked_indices[pos]
            if i in used:
                pos += 1
                continue
            ctx_range = range(max(0, i - context_sentences), min(len(sentences), i + context_sentences + 1))
            new_idx = [j for j in ctx_range if j not in selected and j not in used]
            added_len = sum(len(sentences[j]) + 1 for j in new_idx)
            if total_len + added_len > cap:
                if added_any:
                    break
                pos += 1
                continue
            selected.update(new_idx)
            total_len += added_len
            pos += 1
            added_any = True
        if not selected:
            break
        used.update(selected)
        ordered = sorted(selected)
        slice_text = ' '.join(sentences[i] for i in ordered)[:cap]
        windows.append((slice_text, {
            'method': 'ranked_sentences',
            'window': window_num + 1,
            'keywords': keywords,
            'sentences_matched': len(ranked_indices),
            'sentences_used': len(ordered),
            'chars_used': len(slice_text),
        }))

    if not windows:
        return [(text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'no_windows_built'})]
    return windows


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


def extract_lag(text: str) -> Optional[str]:
    """Pull a recovery-lag phrase ("30 to 120 days", "quarterly", ...) out
    of arbitrary text, same pattern scan_pass_through uses internally.
    Exposed separately so a caller with its OWN already-verified text (e.g.
    an archetype checklist's cost_recovery_mechanism quote) can extract a
    lag from it directly, without re-running the full pass-through scan -
    useful when the scan's own evidence sentences didn't happen to state a
    lag but a DIFFERENT verified source (the checklist answer) did.
    """
    if not text:
        return None
    match = _LAG_RE.search(text)
    return match.group(0) if match else None


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
