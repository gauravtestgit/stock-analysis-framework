# Build an "archetype" module for business-model analysis

## Purpose
Before extracting business details, classify each company (and each reported segment) into a business-model
archetype. Each archetype has a fixed checklist of questions that must be answered from the filing, with quotes.
This replaces open-ended prompts ("what drives this business?") that fall back on industry stereotypes —
e.g. PRDO was described as an edtech platform (Coursera competitors, cloud-cost drivers) instead of a
Title IV-funded university operator.

## Step 0 — fit into the existing code first
Inspect the repo: how filings, sections, XBRL segments, slices, the cache and the LLM provider are currently handled.
Reuse them. Propose where this module plugs in (before the product/competitive/driver analyzers) and wait for my OK.

## 1. Archetype definitions (YAML, one file per archetype under archetypes/)
Schema:
  id, name, description (2–3 lines)
  sic_hints: SIC code ranges that suggest this archetype (hint only, never decisive alone)
  description_cues: phrases that suggest it (e.g. "tuition", "Title IV", "concentrate", "bottling partners", "escalation")
  checklist: list of questions, each with:
    id, question, where_to_look (section/heading keywords for slice selection), answer_type (text | number | enum | list),
    required: true/false
  expected_drivers: driver types this archetype must normally produce (used for validation)
  validation_rules: e.g. "must have funding_cost driver", "must state who bears input costs"

Initial archetypes (write all of these):
- commodity_processor (ALTO, DAR): main inputs/outputs; margin/spread formula; hedging policy; co-products; capacity/utilisation
- pass_through_operator (KEX Marine): escalation/pass-through clauses and lag (use the deterministic pass-through scan result); utilisation; term vs spot mix; contract renewal timing
- branded_staples_franchise (KO): brand portfolio; price/mix vs volume; franchise structure — what the company makes vs bottlers/licensees, and WHO BEARS each input cost; international revenue share and reported FX impact; health/regulatory demand risks
- policy_funded_service (PRDO): share of revenue from government programmes (e.g. 90/10 disclosure); key regulators/rules/accreditation; enrolment/volume trends and cyclicality; customer acquisition/marketing cost; pending regulatory actions
- lender (PGY): funding sources and the benchmark rate they track; credit performance metrics; dependence on securitisation/forward-flow markets; loss provisioning
- subscription_royalty (WMG): recurring revenue sources; pricing power/price increases; churn/renewals; licensing deal cycle
- platform_multi_segment (GOOGL): segment table and weights; per-segment demand drivers; capex intensity; major regulatory/antitrust matters
- single_asset_pharma (ZVRA, HRMY): product revenue concentration; regulatory dates; exclusivity/patent expiry and litigation; sales ramp metrics; cash runway
- industrial_cyclical (CSTM, BLBD): end markets and their cycles; backlog/orders; input metals/energy and pass-through; customer concentration
- other: no checklist forced; output flagged for review

## 2. Classification (two passes, small calls)
Pass A — deterministic evidence pack (no LLM): SIC code from EDGAR, XBRL segment list with revenue weights,
counts of description_cues hits per archetype from the full Business section, net cash vs net debt from XBRL.
Pass B — one small LLM call: give it the evidence pack + the first ~2k chars of the Business overview + the list of
archetype ids and descriptions. It returns, per company AND per reportable segment:
  archetype_id, confidence (0–1), two supporting quotes, runner_up archetype.
Rules:
- If confidence < 0.6 or the top two are within 0.1 → mark "ambiguous", keep both, flag for review.
- Identity check: if the SIC code strongly contradicts the chosen archetype (e.g. SIC 8200 educational services
  classified as anything other than policy_funded_service/subscription), flag and re-run Pass B with that warning.
- Hybrids: each segment gets its own archetype (KEX Marine = pass_through_operator, D&S = industrial_cyclical);
  the company-level archetype is the one with the largest revenue weight, and the report shows the mix.

## 3. Checklist answering (fits the token budget)
- For each checklist question, select a ≤2–3k-char slice using its where_to_look keywords (headings first,
  then keyword-dense paragraphs) from Item 1 / 1A / 7 / 7A, the latest 10-Q MD&A, or the latest 8-K earnings exhibit.
- Batch 2–4 questions per LLM call (same slice region where possible); keep each call ≤ ~3k input tokens;
  space calls/back off for the provider's tokens-per-minute limit.
- Each answer must include: value, quote(s), source (doc, section, period). No quote → answer = "not disclosed".
- Numbers must come from the quote or XBRL; the LLM may not invent or estimate a number.
- Deterministic results (pass-through scan, segment numbers, net cash) are injected as facts, not re-asked.

## 4. Universal evidence gate (applies to this module and all downstream analyzers)
Before rendering, drop any competitor, driver, advantage, value proposition, strength/weakness or rating
justification that lacks a supporting quote. Competitors also need a valid ticker or a quote naming them;
otherwise use "none named in filing".

## 5. Validation against the archetype
- Check expected_drivers and validation_rules; list anything missing as "expected but not found" (e.g. lender with
  no funding-cost driver; franchise with no "who bears input cost" answer; policy_funded_service with no government
  funding share).
- Rate driver direction from the balance sheet: net cash → higher rates are a mild tailwind (interest income);
  net debt → headwind.

## 6. Output (JSON + report section)
{
  "ticker", "as_of", "company_archetype", "confidence", "segment_archetypes": [{segment, weight, archetype, confidence}],
  "evidence_pack": {...}, "checklist": [{question_id, value, quotes, source, status: answered|not_disclosed}],
  "validation": {"missing_expected": [...], "flags": [...]}
}
Report: archetype (+ segment mix), checklist answers with quotes, "expected but not found" list, flags.
Downstream analyzers (product, competitive, drivers) receive the archetype and checklist answers as grounding.

## 7. Caching
Key: (ticker, filing accession(s), module_version), where module_version = hash of archetype YAMLs + prompt templates + slice config.
Any change to a YAML or prompt invalidates automatically. --no-cache flag for development. Log cache hit/miss.

## 8. Tests — regression set with expected classifications
- ALTO → commodity_processor (margin formula answered: ethanol − corn − natural gas + co-products)
- KEX → Marine: pass_through_operator; D&S: industrial_cyclical; fuel pass-through = partial (from the scan)
- KO → branded_staples_franchise; "who bears input costs" answered (bottlers vs company-operated); FX impact quoted from latest 10-Q
- PRDO → policy_funded_service; government funding share quoted; regulators named; no cloud/internet drivers; rate direction from net cash
- PGY → lender; funding benchmark identified (2-year rather than 10-year if the filing says so)
- GOOGL → platform_multi_segment; segment weights from XBRL
Plus: determinism (same filing, same version → identical output); an "other" case doesn't crash; unit tests for the
cue counter, slice selector, identity check, evidence gate and validation rules.

## Deliverable
Run the 6 regression tickers and show me a summary table:
ticker | company archetype | segment archetypes | confidence | checklist answered/total | missing expected | flags
then the full output for PRDO and KO.
