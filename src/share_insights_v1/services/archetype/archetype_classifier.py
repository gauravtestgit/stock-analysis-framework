"""Business-model archetype classification, per archetypes.md at the repo
root (the full spec: 31 archetypes across 7 categories, plus a Universal
Checklist that runs for every company).

Classifies a company (and its reported segments) into a business-model
archetype with its own checklist of questions, answered from the filing with
required evidence quotes. This exists because open-ended "what drives this
business" prompts fall back on industry stereotypes once the real mechanism
is more specific than sector/industry labels suggest - confirmed directly on
KO (Coca-Cola): its real exposure to sugar/corn/aluminum is split between
itself and independent bottlers, which a company-wide "cost_headwind" label
can't represent at all.

Archetypes are auto-discovered from every *.yaml file in ../../archetypes/ -
adding a new one (matching archetypes.md's schema) needs no code change
here. A company that matches none of them classifies as "other" and still
gets the Universal Checklist's Q&A (see _UNIVERSAL_CHECKLIST below) - that's
what catches a company-specific fact (government payer, regulator, FX)
even when no archetype's own checklist applies.

Known remaining scope gap: no 8-K earnings-exhibit text yet (10-K Item 1
Business + latest 10-Q MD&A are both in scope - see
BusinessModelAnalyzer._compute_archetype), and company-level checklist
answering only (segments are classified but their own checklist isn't
separately answered).
"""
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional

import yaml

from ...utils.debug_printer import debug_print
from ...utils.filing_text_tools import select_ranked_windows
from ...utils.json_extractor import extract_json_from_llm_response

_ARCHETYPES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'archetypes')
_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'cache', 'archetype_classifier')

# Per archetypes.md's "Universal Checklist" (section 0): runs for EVERY
# company regardless of archetype match - this is what catches a
# "PRDO-type miss" even when no archetype genuinely fits ("other"), since
# an unmatched company otherwise got zero checklist Q&A at all. Segments,
# balance sheet (net cash/debt), and competitors are deliberately left out
# here - those are already computed deterministically elsewhere
# (SECEdgarProvider's segment_financials, financial_metrics,
# BusinessModelAnalyzer's key_competitors) with real numbers, so re-asking
# the LLM for them here would just be a less reliable duplicate.
_UNIVERSAL_CHECKLIST = [
    {
        'id': 'revenue_model', 'required': True,
        'question': 'How does the company earn revenue (product sale, fee, royalty, rent, interest, tuition, subscription, contract)? Quote the statement.',
        'where_to_look': ['revenue', 'we earn', 'we generate revenue', 'net sales', 'fee', 'royalty', 'subscription'],
    },
    {
        'id': 'customer_concentration', 'required': False,
        'question': 'Does the filing disclose customer concentration (any single customer over 10% of revenue), or government as a payer? Quote it.',
        'where_to_look': ['customer concentration', '10%', 'largest customer', 'government', 'major customer'],
    },
    {
        'id': 'who_bears_key_costs', 'required': True,
        'question': 'For the company\'s major cost lines, does the filing say who bears them - the company itself, customers (via pass-through/escalation), a franchisee/bottler/licensee, or a supplier? Quote the statement.',
        'where_to_look': ['cost of', 'bear', 'pass-through', 'pass through', 'escalation', 'franchisee', 'bottler', 'licensee', 'supplier'],
    },
    {
        'id': 'geography_and_fx', 'required': False,
        'question': 'What % of revenue is earned outside the reporting currency, and what FX impact does the filing quote (from the latest 10-Q or earnings release)?',
        'where_to_look': ['foreign currency', 'international', 'translation', 'exchange rate', 'FX', 'outside the United States'],
    },
    {
        'id': 'regulators_and_rules', 'required': False,
        'question': 'What regulatory agencies, laws, or licenses does the filing name, including any pending actions or litigation? Quote it.',
        'where_to_look': ['regulation', 'regulatory', 'license', 'litigation', 'agency', 'law'],
    },
    {
        'id': 'company_specific_risk_factors', 'required': False,
        'question': 'What risk factor does the filing describe that is specific to this company (not generic/boilerplate like pandemics or climate in general)? Quote it.',
        'where_to_look': ['risk factor', 'risks', 'could adversely affect', 'material adverse'],
    },
    {
        'id': 'latest_quarter_update', 'required': False,
        'question': 'What does the most recent 10-Q or earnings release say about guidance changes or KPI moves? Quote it.',
        'where_to_look': ['guidance', 'outlook', 'this quarter', 'year-over-year', 'compared to the prior'],
    },
]


class ArchetypeClassifier:
    def __init__(self, sec_provider, llm_manager):
        self.sec_provider = sec_provider
        self.llm_manager = llm_manager
        self._archetypes = self._load_archetypes()
        self._module_version = self._compute_module_version()

    # ---------- archetype definitions + versioning ----------

    @staticmethod
    def _load_archetypes() -> Dict[str, Dict[str, Any]]:
        archetypes = {}
        for fname in sorted(os.listdir(_ARCHETYPES_DIR)):
            if fname.endswith('.yaml'):
                with open(os.path.join(_ARCHETYPES_DIR, fname), 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    archetypes[data['id']] = data
        return archetypes

    def _compute_module_version(self) -> str:
        """Hash of the archetype YAMLs + this file's own content, so the
        cache invalidates itself automatically on any change to either -
        no manually-maintained version string to forget to bump. Confirmed
        directly why that matters: BusinessModelAnalyzer's own cache stayed
        stale across an entire batch of fixes because its version string
        was a plain constant nobody remembered to change.
        """
        h = hashlib.sha256()
        for fname in sorted(os.listdir(_ARCHETYPES_DIR)):
            if fname.endswith('.yaml'):
                with open(os.path.join(_ARCHETYPES_DIR, fname), 'rb') as f:
                    h.update(f.read())
        with open(__file__, 'rb') as f:
            h.update(f.read())
        return h.hexdigest()[:16]

    # ---------- cache ----------

    def _cache_path(self, ticker: str, accession_number: str) -> str:
        safe_accession = re.sub(r'[^A-Za-z0-9_-]', '_', accession_number)
        return os.path.join(_CACHE_DIR, f"{ticker}_{safe_accession}_{self._module_version}.json")

    def _read_cache(self, ticker: str, accession_number: Optional[str]) -> Optional[Dict[str, Any]]:
        if not accession_number:
            return None
        path = self._cache_path(ticker, accession_number)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            debug_print(f"[ARCHETYPE_DEBUG] Could not read cache for {ticker}: {e}")
            return None

    def _write_cache(self, ticker: str, accession_number: Optional[str], result: Dict[str, Any]) -> None:
        if not accession_number:
            return
        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            with open(self._cache_path(ticker, accession_number), 'w', encoding='utf-8') as f:
                json.dump(result, f, default=str)
        except Exception as e:
            debug_print(f"[ARCHETYPE_DEBUG] Could not write cache for {ticker}: {e}")

    # ---------- Pass A: deterministic evidence pack (no LLM) ----------

    def _build_evidence_pack(self, ticker: str, full_text: str, segment_financials: Optional[Dict[str, Any]],
                              financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        sic_info = {}
        try:
            sic_info = self.sec_provider.get_company_sic(ticker) or {}
        except Exception as e:
            debug_print(f"[ARCHETYPE_DEBUG] Could not fetch SIC for {ticker}: {e}")

        annual = (segment_financials or {}).get('annual') or {}
        segments = annual.get('segments') or {}
        total_revenue = annual.get('total_revenue') or (sum(d['revenue'] for d in segments.values()) if segments else 0)
        segment_weights = {name: round(d['revenue'] / total_revenue, 3) for name, d in segments.items()} if total_revenue else {}

        text_lower = (full_text or '').lower()
        cue_counts = {
            archetype_id: sum(text_lower.count(cue.lower()) for cue in archetype.get('description_cues', []))
            for archetype_id, archetype in self._archetypes.items()
        }

        total_cash = financial_metrics.get('total_cash', 0) or 0
        total_debt = financial_metrics.get('total_debt', 0) or 0

        return {
            'sic': sic_info.get('sic'),
            'sic_description': sic_info.get('sic_description'),
            'segment_revenue_weights': segment_weights,
            'description_cue_counts': cue_counts,
            'net_cash_vs_debt': total_cash - total_debt,
        }

    # ---------- Pass B: one small LLM call ----------

    @staticmethod
    def _build_segment_context(full_text: str, segment_names: List[str], per_segment_cap: int = 700) -> str:
        """A short text snippet around each segment's own first mention in
        the filing - without this, _classify_with_llm's prompt previously
        gave the LLM nothing but a bare list of segment NAMES plus the
        company-level overview, with no segment-specific text to actually
        distinguish them. Confirmed directly on KO: all five segments
        (EMEA, Latin America, North America, Asia Pacific, Bottling
        Investments) came back classified as branded_staples_franchise at
        an identical 0.9 confidence - the LLM had no way to tell that
        Bottling Investments (a majority-owned manufacturing/bottling
        operation) is a materially different business from the four sales
        regions, which really do share the parent's franchise model.
        """
        if not full_text or not segment_names:
            return ''
        text_lower = full_text.lower()
        blocks = []
        for name in segment_names:
            idx = text_lower.find(name.lower())
            if idx == -1:
                continue
            start = max(0, idx - 100)
            end = min(len(full_text), idx + per_segment_cap)
            snippet = full_text[start:end].strip()
            if snippet:
                blocks.append(f"[{name}]: {snippet}")
        return "\n\n".join(blocks)

    def _classify_with_llm(self, ticker: str, company_name: str, evidence_pack: Dict[str, Any],
                            business_overview: str, segment_names: List[str],
                            segment_context: str = '') -> Dict[str, Any]:
        archetype_list = "\n".join(
            f"- {a['id']}: {a['name']} - {a['description'].strip()}" for a in self._archetypes.values()
        )
        prompt = f"""
Classify {company_name} ({ticker}) into one of these business-model archetypes, based on the evidence below.
If none genuinely fits, use "other" - do not force a fit just to pick one of the listed archetypes.

Archetypes:
{archetype_list}
- other: no listed archetype genuinely fits

Evidence (SIC and description-cue counts are a real constraint, not just a hint: if one archetype's
cue count clearly dominates every other archetype's and its SIC range plausibly matches, you MUST pick
that archetype unless the Business Overview text itself gives a clear, quotable reason to pick a
different one instead - two archetypes can sound similar at a glance (e.g. two transport-sector
archetypes, one contract-based and one spot-market-based) but the cue counts and the text itself are
what actually distinguish them, not surface similarity):
SIC: {evidence_pack.get('sic')} ({evidence_pack.get('sic_description')})
Segment revenue weights: {json.dumps(evidence_pack.get('segment_revenue_weights'))}
Description-cue hit counts per archetype: {json.dumps(evidence_pack.get('description_cue_counts'))}
Net cash vs debt: {evidence_pack.get('net_cash_vs_debt')}

Business Overview (start of the filing's Business section):
{business_overview}

Segments to also classify individually (same archetype list, or "other"): {segment_names}
{f"Segment-specific context - use this, not just the company-level overview above, to classify each segment on its own merits. A segment can genuinely differ from the company as a whole (e.g. a geographic sales region selling the parent's products under its usual model vs. a majority-owned manufacturing/bottling operation):{chr(10)}{segment_context}" if segment_context else ""}

Respond with JSON:
{{
    "company_archetype": "archetype_id or other",
    "confidence": 0.0,
    "runner_up": "archetype_id or null",
    "runner_up_confidence": 0.0,
    "quotes": ["quote 1 copied from the text supporting this classification", "quote 2"],
    "segment_archetypes": [
        {{"segment": "segment name", "archetype": "archetype_id or other", "confidence": 0.0}}
    ]
}}
confidence and runner_up_confidence are both 0-1. Quotes must be copied exactly from the Business Overview text.
"""
        empty_result = {
            'company_archetype': 'other', 'confidence': 0.0, 'runner_up': None,
            'runner_up_confidence': 0.0, 'quotes': [], 'segment_archetypes': [],
        }
        json_str = None
        for attempt in range(2):  # one retry on empty/unparseable - see _answer_checklist for why
            try:
                response = self.llm_manager.generate_response(prompt, temperature=0)
            except Exception as e:
                debug_print(f"[ARCHETYPE_DEBUG] Classification call failed for {ticker} (attempt {attempt + 1}): {e}")
                response = None
            json_str = extract_json_from_llm_response(response) if response else None
            if json_str:
                break
        if not json_str:
            return empty_result
        try:
            return json.loads(json_str)
        except Exception:
            return empty_result

    # ---------- checklist answering (company-level only in this POC) ----------

    @staticmethod
    def _quote_verified(quote: Optional[str], full_text: str) -> bool:
        if not quote or not full_text:
            return False
        normalized_quote = re.sub(r'\s+', ' ', quote.lower()).strip()
        normalized_text = re.sub(r'\s+', ' ', full_text.lower())
        return len(normalized_quote) >= 8 and normalized_quote in normalized_text

    # Was 2 - confirmed directly on real runs (KO, PRDO) that even a
    # 2-question batch still only answers one of its two questions in
    # nearly every batch (e.g. KO's brand_portfolio+price_mix batch: both
    # "not disclosed" despite KO's filing plainly naming its brands a few
    # paragraphs away; PRDO's government_payer_share+regulators_and_
    # accreditors batch: only the second answered). Batching also pools
    # every question's where_to_look keywords into one combined list for
    # slice selection (see _answer_checklist_batch below), so a single
    # question's budget gets diluted by - and can lose entirely to - the
    # other question's keywords (confirmed on PRDO: 149 sentences matched
    # the combined regulatory keyword list, only 10 made the cut, and the
    # one with the real 90/10 answer wasn't among them). One question per
    # call costs more LLM calls but removes both failure modes at once.
    _CHECKLIST_BATCH_SIZE = 1

    # How many ranked windows (see select_ranked_windows) to try before
    # giving up on a question. Confirmed directly why one window wasn't
    # enough even after moving to one-question-per-call and digit-aware
    # ranking: a very common where_to_look keyword (PRDO's "regulator"
    # alone matched 73 sentences, "government program" matched 109) still
    # left only a handful fitting one cap-sized window, and the single
    # window that happened to win the ranking wasn't always the one
    # containing the real answer. Each window costs its own LLM call, so
    # this only escalates past window 1 when window 1 didn't produce a
    # verified quote - most questions resolve in one call either way.
    _MAX_RETRIEVAL_WINDOWS = 3

    def _answer_checklist_batch(self, questions: List[Dict[str, Any]], full_text: str) -> Dict[str, Any]:
        """Answer a checklist question (or small batch - see
        _CHECKLIST_BATCH_SIZE), trying successive ranked text windows until
        one produces a verified quote or the windows run out.

        Confirmed empirically why ONE question per call wasn't by itself
        enough to make answers stable across runs: asking the model to
        answer ALL of a 3-5 question checklist at once (each requiring a
        careful verbatim quote, under a strict "don't invent" instruction)
        had an estimated ~79% per-attempt failure rate originally,
        improved by dropping to one question per call - but a single fixed
        text window built from keyword-length priority alone could still
        miss the sentence that actually answers the question, with no
        second attempt at a DIFFERENT slice when the first one came up
        empty. select_ranked_windows below ranks sentences against the
        question's own words (not just where_to_look) and returns multiple
        non-overlapping candidate windows in rank order for exactly that
        retry.
        """
        keywords = [kw for q in questions for kw in q.get('where_to_look', [])]
        question_text = ' '.join(q['question'] for q in questions)
        windows = select_ranked_windows(full_text, question_text, keywords, cap=2000, max_windows=self._MAX_RETRIEVAL_WINDOWS)
        questions_block = "\n".join(f"{i + 1}. [{q['id']}] {q['question']}" for i, q in enumerate(questions))

        parsed_answers: Dict[str, Any] = {}
        slice_meta: Dict[str, Any] = {}
        for window_idx, (slice_text, window_meta) in enumerate(windows):
            prompt = f"""
Using ONLY the filing text below, answer each question. For each, give a value and a short quote copied EXACTLY
from the text that supports it. If the text doesn't address a question, respond with value "Not disclosed" and
quote null - do not guess, estimate, or invent a number.

Filing text:
{slice_text}

Questions:
{questions_block}

Respond with JSON:
{{
    "answers": [
        {{"id": "question_id", "value": "answer or Not disclosed", "quote": "exact quote or null"}}
    ]
}}
"""
            try:
                response = self.llm_manager.generate_response(prompt, temperature=0)
            except Exception as e:
                debug_print(f"[ARCHETYPE_DEBUG] Checklist call failed (window {window_idx + 1}): {e}")
                response = None
            json_str = extract_json_from_llm_response(response) if response else None
            answers_list = []
            if json_str:
                try:
                    answers_list = json.loads(json_str).get('answers', [])
                except Exception:
                    answers_list = []
            any_real_quote = any(a.get('quote') for a in answers_list)
            slice_meta = {**window_meta, 'window_tried': window_idx + 1, 'windows_available': len(windows)}
            if any_real_quote or window_idx == len(windows) - 1:
                parsed_answers = {a.get('id'): a for a in answers_list}
                break
            debug_print(f"[ARCHETYPE_DEBUG] Window {window_idx + 1}/{len(windows)} had no real quotes, trying next window")

        return parsed_answers, slice_meta

    def _answer_checklist(self, checklist: List[Dict[str, Any]], full_text: str) -> List[Dict[str, Any]]:
        """Generic over any plain checklist item list - an archetype's own
        checklist, or the Universal Checklist (_UNIVERSAL_CHECKLIST above),
        which isn't tied to any single archetype."""
        if not checklist or not full_text:
            return [{'question_id': q['id'], 'value': 'Not disclosed', 'quotes': [], 'status': 'not_disclosed'} for q in checklist], {'method': 'no_text'}

        parsed_answers: Dict[str, Any] = {}
        slice_metas = []
        for batch_start in range(0, len(checklist), self._CHECKLIST_BATCH_SIZE):
            batch = checklist[batch_start:batch_start + self._CHECKLIST_BATCH_SIZE]
            batch_answers, batch_slice_meta = self._answer_checklist_batch(batch, full_text)
            parsed_answers.update(batch_answers)
            slice_metas.append(batch_slice_meta)

        results = []
        for q in checklist:
            raw = parsed_answers.get(q['id'])
            quote = raw.get('quote') if raw else None
            verified = self._quote_verified(quote, full_text)
            results.append({
                'question_id': q['id'],
                'question': q['question'],
                'value': raw.get('value', 'Not disclosed') if (raw and verified) else 'Not disclosed',
                'quotes': [quote] if verified else [],
                'status': 'answered' if verified else 'not_disclosed',
                'required': q.get('required', False),
            })
        return results, {'method': 'batched_keyword_sentences', 'batches': slice_metas}

    @staticmethod
    def _validate(checklist_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        missing = [
            f"{a['question_id']} ({a['question']})"
            for a in checklist_answers
            if a.get('required') and a.get('status') != 'answered'
        ]
        return {'missing_expected': missing, 'flags': []}

    # ---------- orchestration ----------

    def classify(self, ticker: str, company_name: str, full_text: str,
                 segment_financials: Optional[Dict[str, Any]], financial_metrics: Dict[str, Any],
                 accession_number: Optional[str] = None) -> Dict[str, Any]:
        cached = self._read_cache(ticker, accession_number)
        if cached is not None:
            debug_print(f"[ARCHETYPE_DEBUG] Using cached archetype classification for {ticker}")
            return cached

        evidence_pack = self._build_evidence_pack(ticker, full_text, segment_financials, financial_metrics)
        business_overview = (full_text or '')[:2000]
        segment_names = list((segment_financials or {}).get('annual', {}).get('segments', {}).keys())
        segment_context = self._build_segment_context(full_text, segment_names)

        classification = self._classify_with_llm(
            ticker, company_name, evidence_pack, business_overview, segment_names, segment_context
        )

        company_archetype_id = classification.get('company_archetype', 'other')
        archetype = self._archetypes.get(company_archetype_id)
        if archetype:
            checklist_answers, slice_meta = self._answer_checklist(archetype.get('checklist', []), full_text)
            validation = self._validate(checklist_answers)
        else:
            checklist_answers, slice_meta, validation = [], {'method': 'no_archetype_matched'}, {'missing_expected': [], 'flags': []}

        # Universal Checklist (archetypes.md section 0) runs regardless of
        # whether an archetype matched - this is what gives an "other"
        # company (confirmed on PRDO: no archetype in the original 2-item
        # POC roster fit it) SOME grounded, quote-verified Q&A instead of
        # nothing at all.
        universal_checklist_answers, universal_slice_meta = self._answer_checklist(_UNIVERSAL_CHECKLIST, full_text)

        confidence = classification.get('confidence') or 0.0
        runner_up_confidence = classification.get('runner_up_confidence') or 0.0
        if confidence < 0.6 or (classification.get('runner_up') and abs(confidence - runner_up_confidence) < 0.1):
            validation['flags'].append('ambiguous classification')

        # Deterministic backstop, not a re-ask: with 30+ archetypes now
        # competing (vs. the original 2), a couple of surface-similar ones
        # (e.g. two transport-sector archetypes, one contract-based and one
        # spot-market-based) can read alike to the LLM even when the
        # deterministic cue counts overwhelmingly favor one of them -
        # confirmed directly on KEX (pass_through_operator: 35 cue hits vs.
        # cyclical_transport's 1) picking the wrong one despite the prompt
        # already being told cue counts are a real constraint. This doesn't
        # override the LLM's pick - it flags a mismatch so it's visible and
        # checkable, same philosophy as this analyzer's other confirmation
        # flags (e.g. driver-direction vs. observed correlation).
        cue_counts = evidence_pack.get('description_cue_counts') or {}
        if cue_counts:
            top_archetype_id = max(cue_counts, key=cue_counts.get)
            top_count = cue_counts[top_archetype_id]
            chosen_count = cue_counts.get(company_archetype_id, 0)
            if top_archetype_id != company_archetype_id and top_count >= 5 and top_count >= 3 * max(chosen_count, 1):
                validation['flags'].append(
                    f"cue_count_mismatch: chosen '{company_archetype_id}' ({chosen_count} cue hits) vs. "
                    f"'{top_archetype_id}' ({top_count} cue hits)"
                )

        # Rule 4 in archetypes.md: "'other' <= 0.5 confidence" - a weak-fit
        # classification should resolve to "other" in the first place (the
        # classify_with_llm prompt already says so), but this clamps the
        # number itself so a stray high-confidence "other" never reads as a
        # confident classification downstream (e.g. in the Type-override
        # lookup, which already only acts on a matched archetype, but other
        # future readers of this field shouldn't have to know that).
        if company_archetype_id == 'other' and confidence > 0.5:
            confidence = 0.5

        result = {
            'ticker': ticker,
            'company_archetype': company_archetype_id,
            'confidence': confidence,
            'quotes': classification.get('quotes', []),
            'runner_up': classification.get('runner_up'),
            'segment_archetypes': classification.get('segment_archetypes', []),
            'evidence_pack': evidence_pack,
            'checklist': checklist_answers,
            'checklist_slice_meta': slice_meta,
            'universal_checklist': universal_checklist_answers,
            'universal_checklist_slice_meta': universal_slice_meta,
            'expected_drivers': archetype.get('expected_drivers', []) if archetype else [],
            'validation': validation,
        }
        self._write_cache(ticker, accession_number, result)
        return result
