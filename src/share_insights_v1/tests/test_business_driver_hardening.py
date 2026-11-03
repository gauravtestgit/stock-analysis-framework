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
    test_kex_golden_assertions()
    test_ko_golden_assertions()
    test_determinism()

    print(f"\n{'='*60}")
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")
    if FAIL:
        print("Failed checks:", FAIL)
        sys.exit(1)
