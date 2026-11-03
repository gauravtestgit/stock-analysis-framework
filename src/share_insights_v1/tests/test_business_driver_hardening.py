#!/usr/bin/env python3
"""Verification script for the business-driver-map hardening batch:
structured segment numbers, deterministic pass-through scanning, competitor
dedup/validation, consistency checks, and run-to-run determinism via the
filing-keyed cache.

Run directly (standalone script, matching this repo's existing test files -
not pytest): python -m share_insights_v1.tests.test_business_driver_hardening
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ..implementations.data_providers.sec_edgar_provider import SECEdgarProvider
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.analyzers.business_model_analyzer import BusinessModelAnalyzer
from ..implementations.llm_providers.llm_manager import LLMManager
from ..utils.filing_text_tools import split_sentences, select_keyword_context, scan_pass_through

PASS = []
FAIL = []


def check(name: str, condition: bool, detail: str = ""):
    if condition:
        PASS.append(name)
        print(f"  PASS: {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL: {name} {detail}")


def test_filing_text_tools_units():
    """No network calls - fixed inline text, so these are fast and can't
    be flaky from a live filing changing or a network hiccup."""
    print("\n=== filing_text_tools unit checks ===")

    sentences = split_sentences("First sentence. Second sentence! Third one? Fourth.")
    check("split_sentences splits on . ! ?", len(sentences) == 4, f"got {sentences}")

    text = (
        "The Company is a leader in widgets. Competition in the widget industry is intense. "
        "The Company does not discuss pricing. Jones Act compliance is required for domestic trade."
    )
    slice_text, meta = select_keyword_context(text, ["Jones Act", "Competition"], cap=5000)
    check("select_keyword_context finds keyword sentences", meta['method'] == 'keyword_sentences', meta)
    check("select_keyword_context slice contains Jones Act", 'Jones Act' in slice_text)

    fuel_text = (
        "The Company's contracts typically include fuel escalation clauses. "
        "The rate may or may not include escalation provisions to recover changes in specific costs such as fuel. "
        "The Company also leases office space in several cities."
    )
    fuel_result = scan_pass_through(fuel_text, ["fuel", "diesel"])
    check("scan_pass_through finds fuel pass-through", fuel_result is not None and fuel_result['strength'] == 'partial', fuel_result)

    corn_result = scan_pass_through(fuel_text, ["corn", "agricultural feedstock"])
    check("scan_pass_through returns None for an absent driver", corn_result is None, corn_result)

    generic_term_result = scan_pass_through(fuel_text, ["rate"])
    check("scan_pass_through filters overly generic terms like 'rate'", generic_term_result is None, generic_term_result)


# Invented placeholder strings that must never reach a real report - found
# leaking into KEX's core_products on a run where the LLM call failed and
# silently fell through to _get_fallback_product_analysis, with nothing
# distinguishing "Primary Product"/"Secondary Product" from a real,
# filing-sourced answer like "tank barges, generators, electric fracturing
# systems". _get_fallback_product_analysis no longer invents any of these
# (core_products is now an empty list there), but this check guards against
# a regression reintroducing placeholder text in that function or any other
# fallback path.
_KNOWN_PLACEHOLDER_STRINGS = {
    'primary product', 'secondary product', 'software platform', 'cloud services',
    'consumer products', 'brand portfolio', 'industry peers', 'market position',
}


def check_no_placeholders(label: str, values) -> None:
    found = [v for v in (values or []) if isinstance(v, str) and v.strip().lower() in _KNOWN_PLACEHOLDER_STRINGS]
    check(f"{label} contains no known placeholder strings", not found, found)


def test_no_placeholder_values():
    """No network calls - exercises the fallback path directly rather than
    relying on a live LLM call happening to fail during this test run."""
    print("\n=== Placeholder-value regression check (no network) ===")
    sec_provider = SECEdgarProvider()
    analyzer = BusinessModelAnalyzer(YahooFinanceProvider(), None, sec_provider)

    for sector in ['Industrials', 'Technology', 'Consumer Defensive', 'Unknown']:
        fallback = analyzer._get_fallback_product_analysis(sector, 'Some Industry')
        check_no_placeholders(f"_get_fallback_product_analysis({sector!r}).core_products", fallback.get('core_products'))

    comp_fallback = analyzer._get_fallback_competitive_analysis('Some Industry')
    check_no_placeholders("_get_fallback_competitive_analysis.key_competitors", comp_fallback.get('key_competitors'))


def test_kex_golden_assertions():
    print("\n=== KEX golden assertions (live SEC/Yahoo/LLM data) ===")
    sec_provider = SECEdgarProvider()
    yahoo_provider = YahooFinanceProvider()
    llm_manager = LLMManager()
    analyzer = BusinessModelAnalyzer(yahoo_provider, llm_manager, sec_provider)

    fm = yahoo_provider.get_financial_metrics("KEX")
    result = analyzer.analyze("KEX", {
        'financial_metrics': fm,
        'company_info': {'sector': fm.get('sector', ''), 'industry': fm.get('industry', '')},
    })

    segments = result.get('segment_revenue_data', {}).get('primary_segments', [])
    check("KEX has exactly 2 real segments", len(segments) == 2, f"got {[s.get('segment_name') for s in segments]}")

    marine = next((s for s in segments if 'marine' in s.get('segment_name', '').lower() or s.get('segment_name') == 'KMT'), None)
    other = next((s for s in segments if s is not marine), None) if marine else None
    if marine:
        check("Marine segment ~55-60% of revenue", 55 <= marine.get('revenue_percentage', 0) <= 60, marine.get('revenue_percentage'))
        check("No container shipping segment invented", not any('container' in s.get('segment_name', '').lower() for s in segments))
    if marine and other and marine.get('profit') is not None and other.get('profit') is not None and marine.get('revenue') and other.get('revenue'):
        marine_margin = marine['profit'] / marine['revenue']
        other_margin = other['profit'] / other['revenue']
        check("Marine margin > Distribution & Services margin", marine_margin > other_margin, f"{marine_margin:.3f} vs {other_margin:.3f}")

    # The LLM is free to name a Jones Act driver as a headwind in the first
    # place (that's its own call, not something to prevent) - what this
    # check actually verifies is the consistency validator's job: WHEN that
    # happens alongside Jones Act also being listed as an advantage, it must
    # be flagged, not silently left looking like two parts of the report
    # disagree with each other.
    comp = result.get('competitive_differentiation', {})
    advantages_text = ' '.join(comp.get('competitive_advantages') or []).lower()
    jones_act_in_advantages = 'jones act' in advantages_text
    jones_act_headwind_drivers = [
        d for d in comp.get('business_drivers') or []
        if 'jones' in (d.get('driver_name') or '').lower() and d.get('exposure') in ('cost_headwind', 'revenue_headwind')
    ]
    if jones_act_in_advantages and jones_act_headwind_drivers:
        for driver in jones_act_headwind_drivers:
            check("Jones Act headwind driver is flagged inconsistent with the advantages list",
                  'consistency_flags' in driver, driver)
    else:
        check("No Jones Act advantage/headwind contradiction present this run (nothing to flag)", True)

    diesel_like = [d for d in comp.get('business_drivers') or [] if any(
        term in (d.get('driver_name') or '').lower() for term in ['fuel', 'diesel', 'bunker']
    )]
    check("A fuel/diesel/bunker driver was identified", len(diesel_like) > 0, [d.get('driver_name') for d in comp.get('business_drivers') or []])

    demand_side_drivers = [d for d in comp.get('business_drivers') or [] if d.get('driver_type') == 'demand_side']
    check("No demand-side driver is given a commodity ticker",
          all(d.get('ticker_symbol') is None for d in demand_side_drivers),
          demand_side_drivers)

    check("KEX classified as pass_through_operator archetype",
          result.get('archetype', {}).get('company_archetype') == 'pass_through_operator',
          result.get('archetype'))
    check("KEX's Type derives from the archetype, not a generic sector/industry default",
          result.get('business_model_type') == 'Pass-Through Operator', result.get('business_model_type'))

    # KEX's required cost_recovery_mechanism answer must show up somewhere -
    # either covered by a driver's pass_through scan, or explicitly listed
    # as a gap - never silently absent from the report either way.
    required_answered = [i for i in result.get('archetype', {}).get('checklist', []) if i.get('required') and i.get('status') == 'answered']
    expected_but_not_found_ids = {i['question_id'] for i in comp.get('expected_but_not_found') or []}
    drivers_with_pass_through = [d for d in comp.get('business_drivers') or [] if d.get('pass_through')]
    for item in required_answered:
        if item['question_id'] == 'cost_recovery_mechanism':
            check("KEX's cost_recovery_mechanism is covered by a pass_through driver or listed as expected-but-not-found",
                  len(drivers_with_pass_through) > 0 or item['question_id'] in expected_but_not_found_ids,
                  {"drivers": comp.get('business_drivers'), "expected_but_not_found": comp.get('expected_but_not_found')})

    check("KEX's report-level consistency_flags is present (ran, even if empty)",
          'consistency_flags' in result, result.get('consistency_flags'))
    check("KEX's Type matches its archetype - no 'Type vs archetype' consistency flag",
          not any('Type is' in f for f in result.get('consistency_flags') or []),
          result.get('consistency_flags'))

    segment_archetypes = result.get('archetype', {}).get('segment_archetypes') or []
    check("KEX has a per-segment archetype for both KMT and the Distribution and Services segment",
          len(segment_archetypes) >= 2, segment_archetypes)


def test_ko_golden_assertions():
    """KO's 10-K uses a different XBRL rendering convention than KEX's for
    both the segment-detail table (no "[Member]" suffix at all - a bare
    "EMEA | Operating Segments" merged cell instead) and the Item 1 Business
    heading (surrounded by cross-references to itself from Risk Factors) -
    confirmed both were silently returning nothing/wrong before the fix."""
    print("\n=== KO golden assertions (live SEC/Yahoo/LLM data) ===")
    sec_provider = SECEdgarProvider()
    yahoo_provider = YahooFinanceProvider()
    llm_manager = LLMManager()
    analyzer = BusinessModelAnalyzer(yahoo_provider, llm_manager, sec_provider)

    fm = yahoo_provider.get_financial_metrics("KO")
    result = analyzer.analyze("KO", {
        'financial_metrics': fm,
        'company_info': {'sector': fm.get('sector', ''), 'industry': fm.get('industry', '')},
    })

    segments = result.get('segment_revenue_data', {}).get('primary_segments', [])
    check("KO has at least 4 real geographic/operating segments (not the LLM-estimate fallback)",
          len(segments) >= 4, [s.get('segment_name') for s in segments])
    check("KO segments include EMEA (a real reported segment, not invented)",
          any('emea' in s.get('segment_name', '').lower() for s in segments))
    check("KO's structured-data path was used (not the LLM-estimate fallback)",
          result.get('slice_log', {}).get('segment_revenue_data', {}).get('method') == 'structured_filing_data_no_llm',
          result.get('slice_log', {}).get('segment_revenue_data'))

    # KO's reported segments sum to slightly more than its real consolidated
    # revenue (confirmed directly: $48.806B segment sum vs $47.941B
    # consolidated - a ~1.8% intersegment-elimination gap) - that gap is now
    # surfaced as its own explicit "Corporate / Eliminations" line (rather
    # than left as unexplained rounding error), so the full set of segments
    # sums to ~100% of consolidated revenue, and the reconciling line itself
    # should be visible and negative (KO's segment sum exceeds its real
    # consolidated total).
    segment_pct_sum = sum(s.get('revenue_percentage', 0) for s in segments)
    check("KO's segment percentages (incl. the Corporate/Eliminations reconciling line) sum to ~100% of consolidated revenue",
          abs(segment_pct_sum - 100) < 0.5, segment_pct_sum)
    reconciliation_line = next((s for s in segments if s.get('segment_name') == 'Corporate / Eliminations'), None)
    check("KO's segment breakdown surfaces an explicit Corporate/Eliminations reconciling line",
          reconciliation_line is not None and reconciliation_line.get('revenue_percentage', 0) < 0,
          reconciliation_line)

    # KO's segment names (EMEA etc.) are first mentioned in an unrelated
    # Costa/innocent/dogadan corporate-restructuring footnote, not near the
    # real brand list - confirmed this fed core_products a mid-sentence
    # fragment about segment-reporting treatment instead of KO's actual
    # flagship brands, until product_portfolio slicing was changed to prefer
    # a brand/trademark keyword slice over the segment-overview one.
    core_products = result.get('product_portfolio', {}).get('core_products') or []
    check("KO's product_portfolio slice used the brand/trademark keyword path, not the segment-overview one",
          result.get('slice_log', {}).get('product_portfolio', {}).get('method') == 'keyword_sentences',
          result.get('slice_log', {}).get('product_portfolio'))
    check("KO's core_products names a real flagship brand, not an acquisition-footnote fragment",
          any(b in ' '.join(core_products) for b in ['Coca-Cola', 'Sprite', 'Fanta', 'Diet Coke']),
          core_products)

    comp = result.get('competitive_differentiation', {})
    competitor_names = ' '.join(c.get('name', '') for c in comp.get('key_competitors') or []).lower()
    check("KO's real named competitor (PepsiCo) is found, not the 'no competitors' fallback",
          'pepsi' in competitor_names, comp.get('key_competitors') or comp.get('key_competitors_note'))

    archetype = result.get('archetype', {})
    check("KO classified as branded_staples_franchise archetype",
          archetype.get('company_archetype') == 'branded_staples_franchise', archetype)
    check("KO's Type derives from the archetype, not the generic sector/industry 'Manufacturing' default",
          result.get('business_model_type') == 'Branded Staples Franchise', result.get('business_model_type'))

    # KO's cost_bearer_split answer (bottling partners bear the main input
    # costs) should structurally mute the input-cost drivers' exposure
    # label, not rely on the LLM's own driver text to mention it - confirmed
    # directly that the LLM's relationship text for these drivers didn't
    # mention bottling partners even with the same verified answer in its
    # prompt context.
    input_cost_drivers = [
        d for d in comp.get('business_drivers') or []
        if d.get('driver_type') == 'commodity_input' and d.get('channel') == 'cost'
    ]
    check("KO has at least one input-cost driver to check cost_bearer muting on",
          len(input_cost_drivers) > 0, input_cost_drivers)
    check("KO's input-cost drivers carry a cost_bearer field (bottling partners bear the cost)",
          all(d.get('cost_bearer', {}).get('strength') in ('full', 'partial') for d in input_cost_drivers),
          input_cost_drivers)

    # KO's required international_revenue_and_fx answer must show up
    # somewhere - either as an actual "fx" driver, or explicitly listed as
    # a gap - confirmed directly this answer was previously just dropped
    # with no fx driver anywhere in the report and nothing flagging that.
    fx_drivers = [d for d in comp.get('business_drivers') or [] if d.get('driver_type') == 'fx']
    expected_but_not_found_ids = {i['question_id'] for i in comp.get('expected_but_not_found') or []}
    for item in archetype.get('checklist', []):
        if item.get('required') and item.get('status') == 'answered' and item['question_id'] == 'international_revenue_and_fx':
            check("KO's international_revenue_and_fx is covered by an fx driver or listed as expected-but-not-found",
                  len(fx_drivers) > 0 or 'international_revenue_and_fx' in expected_but_not_found_ids,
                  {"drivers": comp.get('business_drivers'), "expected_but_not_found": comp.get('expected_but_not_found')})

    check("KO's report-level consistency_flags is present (ran, even if empty)",
          'consistency_flags' in result, result.get('consistency_flags'))
    check("KO's Type matches its archetype - no 'Type vs archetype' consistency flag",
          not any('Type is' in f for f in result.get('consistency_flags') or []),
          result.get('consistency_flags'))

    segment_archetypes = archetype.get('segment_archetypes') or []
    check("KO has a per-segment archetype including its Bottling Investments segment",
          any('bottling' in (seg.get('segment') or '').lower() for seg in segment_archetypes),
          segment_archetypes)


def test_determinism():
    print("\n=== Determinism via filing-keyed cache ===")
    yahoo_provider = YahooFinanceProvider()
    llm_manager = LLMManager()
    analyzer = BusinessModelAnalyzer(yahoo_provider, llm_manager, SECEdgarProvider())
    fm = yahoo_provider.get_financial_metrics("KEX")
    data = {'financial_metrics': fm, 'company_info': {'sector': fm.get('sector', ''), 'industry': fm.get('industry', '')}}

    first = analyzer.analyze("KEX", data)
    second = analyzer.analyze("KEX", data)
    check("Same filing analyzed twice returns identical result", first == second)


if __name__ == "__main__":
    test_filing_text_tools_units()
    test_no_placeholder_values()
    test_kex_golden_assertions()
    test_ko_golden_assertions()
    test_determinism()

    print(f"\n{'='*60}")
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")
    if FAIL:
        print("Failed checks:", FAIL)
        sys.exit(1)
