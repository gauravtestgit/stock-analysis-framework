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

    comp = result.get('competitive_differentiation', {})
    advantages_text = ' '.join(comp.get('competitive_advantages') or []).lower()
    jones_act_in_advantages = 'jones act' in advantages_text
    jones_act_as_headwind = any(
        'jones' in (d.get('driver_name') or '').lower() and d.get('exposure') in ('cost_headwind', 'revenue_headwind')
        for d in comp.get('business_drivers') or []
    )
    check("Jones Act not simultaneously an advantage and an unflagged headwind",
          not (jones_act_in_advantages and jones_act_as_headwind),
          "contradiction not flagged" if (jones_act_in_advantages and jones_act_as_headwind) else "")

    for driver in comp.get('business_drivers') or []:
        if 'jones' in (driver.get('driver_name') or '').lower() and driver.get('exposure') in ('cost_headwind', 'revenue_headwind'):
            check(f"Jones Act headwind driver is flagged inconsistent", 'consistency_flags' in driver, driver)

    diesel_like = [d for d in comp.get('business_drivers') or [] if any(
        term in (d.get('driver_name') or '').lower() for term in ['fuel', 'diesel', 'bunker']
    )]
    check("A fuel/diesel/bunker driver was identified", len(diesel_like) > 0, [d.get('driver_name') for d in comp.get('business_drivers') or []])


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
    test_determinism()

    print(f"\n{'='*60}")
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")
    if FAIL:
        print("Failed checks:", FAIL)
        sys.exit(1)
