import re
import requests
import json
from typing import Dict, Any, Optional, List
from ...interfaces.sec_data_provider import SECDataProvider
import time
from ...utils.debug_printer import debug_print

_RE_NUMERIC = re.compile(r'^-?\d+(\.\d+)?$')

class SECEdgarProvider(SECDataProvider):
    """SEC EDGAR API data provider for financial filings"""
    
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.cik_retrieval_url = "https://sec.gov"
        self.headers = {
            'User-Agent': 'StockAnalysisFramework admin@stockanalysis.dev',
            'Accept-Encoding': 'gzip, deflate'
        }
        self.rate_limit_delay = 0.1  # SEC requires 10 requests per second max
    
    def get_latest_10k(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get latest 10-K filing data"""
        try:
            cik = self._get_cik(ticker)
            if not cik:
                return None
            
            # Get company filings
            filings_url = f"{self.base_url}/submissions/CIK{cik:010d}.json"
            response = requests.get(filings_url, headers=self.headers)
            time.sleep(self.rate_limit_delay)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            filings = data.get('filings', {}).get('recent', {})
            
            # Find latest 10-K
            for i, form in enumerate(filings.get('form', [])):
                if form == '10-K':
                    return {
                        'form': form,
                        'filing_date': filings['filingDate'][i],
                        'accession_number': filings['accessionNumber'][i],
                        'primary_document': filings['primaryDocument'][i]
                    }
            
            return None
            
        except Exception as e:
            debug_print(f"Error fetching 10-K for {ticker}: {e}")
            return None
    
    def get_latest_10q(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get latest 10-Q filing data"""
        try:
            cik = self._get_cik(ticker)
            if not cik:
                return None
            
            filings_url = f"{self.base_url}/submissions/CIK{cik:010d}.json"
            response = requests.get(filings_url, headers=self.headers)
            time.sleep(self.rate_limit_delay)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            filings = data.get('filings', {}).get('recent', {})
            
            # Find latest 10-Q
            for i, form in enumerate(filings.get('form', [])):
                if form == '10-Q':
                    return {
                        'form': form,
                        'filing_date': filings['filingDate'][i],
                        'accession_number': filings['accessionNumber'][i],
                        'primary_document': filings['primaryDocument'][i]
                    }
            
            return None
            
        except Exception as e:
            debug_print(f"Error fetching 10-Q for {ticker}: {e}")
            return None
    
    def get_filing_facts(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get company facts from SEC API"""
        try:
            cik = self._get_cik(ticker)
            if not cik:
                return None
            
            facts_url = f"{self.base_url}/api/xbrl/companyfacts/CIK{cik:010d}.json"
            response = requests.get(facts_url, headers=self.headers)
            time.sleep(self.rate_limit_delay)
            
            if response.status_code != 200:
                return None
            
            return response.json()
            
        except Exception as e:
            debug_print(f"Error fetching facts for {ticker}: {e}")
            return None
    
    def _get_cik(self, ticker: str) -> Optional[int]:
        """Get CIK number for ticker"""
        try:
            # Use SEC company tickers endpoint
            tickers_url = f"{self.cik_retrieval_url}/files/company_tickers.json"
            response = requests.get(tickers_url, headers=self.headers)
            time.sleep(self.rate_limit_delay)
            
            if response.status_code != 200:
                debug_print(f"Failed to fetch tickers: {response.status_code}")
                return None
            
            data = response.json()
            
            # Search through the numbered entries
            for entry in data.values():
                if entry.get('ticker', '').upper() == ticker.upper():
                    return entry.get('cik_str')
            
            return None
            
        except Exception as e:
            debug_print(f"Error getting CIK for {ticker}: {e}")
            return None
    
    def get_management_data(self, ticker: str) -> Dict[str, Any]:
        """Get management data from SEC filings (DEF 14A proxy statements)"""
        try:
            cik = self._get_cik(ticker)
            if not cik:
                return {'error': f'CIK not found for {ticker}'}
            
            # Get company filings
            filings_url = f"{self.base_url}/submissions/CIK{cik:010d}.json"
            response = requests.get(filings_url, headers=self.headers)
            time.sleep(self.rate_limit_delay)
            
            if response.status_code != 200:
                return {'error': f'Failed to fetch filings: {response.status_code}'}
            
            data = response.json()
            filings = data.get('filings', {}).get('recent', {})
            
            # Find recent proxy statements (DEF 14A)
            proxy_filings = []
            for i, form in enumerate(filings.get('form', [])):
                if form == 'DEF 14A' and len(proxy_filings) < 2:
                    proxy_filings.append({
                        'form': form,
                        'filing_date': filings['filingDate'][i],
                        'accession_number': filings['accessionNumber'][i],
                        'primary_document': filings['primaryDocument'][i]
                    })
            
            if not proxy_filings:
                return {'error': 'No recent proxy statements found'}
            
            # Extract basic management info
            management_metrics = {
                'proxy_filings_found': len(proxy_filings),
                'latest_proxy_date': proxy_filings[0]['filing_date'] if proxy_filings else None,
                'executive_compensation_disclosed': True,  # Proxy statements always contain this
                'board_composition_disclosed': True,
                'insider_ownership_disclosed': True
            }
            
            return {
                'ticker': ticker,
                'cik': cik,
                'management_metrics': management_metrics,
                'data_source': 'SEC EDGAR'
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _archive_dir_url(self, cik: int, filing_data: Dict[str, Any]) -> str:
        """Base archive directory URL for a filing (hyphens stripped from the
        accession number, matching SEC's directory naming), used to build
        FilingSummary.xml / R#.htm URLs alongside the primary document."""
        accession = filing_data['accession_number'].replace('-', '')
        return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}"

    def _fetch_filing_document(self, cik: int, filing_data: Dict[str, Any]) -> Optional[str]:
        """Fetch a filing's primary document HTML, trying the URL formats SEC
        actually serves documents from. data.sec.gov (self.base_url) is the
        XBRL/JSON API host and reliably 404s on document fetches - confirmed
        directly - so www.sec.gov is tried too; kept as a fallback list since
        that was the original (if accidental) design here."""
        accession = filing_data['accession_number'].replace('-', '')
        primary_doc = filing_data['primary_document']
        possible_urls = [
            f"{self.base_url}/Archives/edgar/data/{cik}/{accession}/{primary_doc}",
            f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_doc}",
            f"{self.base_url}/Archives/edgar/data/{cik}/{filing_data['accession_number']}/{primary_doc}"
        ]
        for doc_url in possible_urls:
            debug_print(f"[SEC_DEBUG] Trying URL: {doc_url}")
            response = requests.get(doc_url, headers=self.headers)
            time.sleep(self.rate_limit_delay)
            if response.status_code == 200:
                debug_print(f"[SEC_DEBUG] Success with URL: {doc_url}")
                return response.text
            debug_print(f"[SEC_DEBUG] Failed with status {response.status_code}: {doc_url}")
        return None

    def get_business_description(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get the full Item 1 Business section from the latest 10-K filing.

        Returns the full extracted section (tens of thousands of characters
        for a real filing), uncapped - callers select the slice they need
        per use case (e.g. a ~5k-char window around competition-related
        sentences for one prompt, segment-heading paragraphs for another)
        rather than this provider deciding one fixed cutoff for everyone.
        """
        try:
            debug_print(f"[SEC_DEBUG] Getting business description for {ticker}")
            cik = self._get_cik(ticker)
            if not cik:
                debug_print(f"[SEC_DEBUG] No CIK found for {ticker}")
                return None

            debug_print(f"[SEC_DEBUG] Found CIK {cik} for {ticker}")
            filing_data = self.get_latest_10k(ticker)
            if not filing_data:
                debug_print(f"[SEC_DEBUG] No 10-K filing found for {ticker}")
                return None

            debug_print(f"[SEC_DEBUG] Found 10-K filing for {ticker}: {filing_data['accession_number']}")

            content = self._fetch_filing_document(cik, filing_data)
            if not content:
                debug_print(f"[SEC_DEBUG] All URL formats failed for {ticker}")
                return None

            debug_print(f"[SEC_DEBUG] Document fetched successfully, size: {len(content)} chars")
            business_section = self._extract_business_section(content)

            debug_print(f"[SEC_DEBUG] Business section extracted: {len(business_section)} chars")

            return {
                'ticker': ticker,
                'filing_date': filing_data['filing_date'],
                'accession_number': filing_data['accession_number'],
                'business_description': business_section,
                'data_source': 'SEC 10-K Filing'
            }

        except Exception as e:
            debug_print(f"[SEC_DEBUG] Error fetching business description for {ticker}: {e}")
            import traceback
            traceback.debug_print_exc()
            return None
    
    def _extract_business_section(self, content: str) -> str:
        """Extract Item 1 - Business section from 10-K filing.

        A 10-K's table of contents also contains an "Item 1. Business" entry,
        immediately followed by a page number and the next item's title - and
        textually that's indistinguishable from a real heading to a simple
        first-match regex, which is what this used to do. Confirmed directly
        on KEX's real 10-K: "item 1. business" occurs exactly once, in the
        TOC; the TOC then separately lists "Item 1A. Risk Factors" and
        "Item 2. Properties" entries only ~900 chars later (the TOC also
        lists many non-Item subsection titles in between, so entry-to-entry
        gaps within the TOC aren't tiny, but confirmed to stay under ~1000
        chars) - so taking the NEAREST following "Item 1A"/"Item 2" match (the
        previous fix's bug) still lands inside the TOC. The real "Item 1A.
        Risk Factors" heading is ~96,000 characters further on, immediately
        preceded by real prose (confirmed: executive bios) and followed by
        real Risk Factors prose - i.e. the real section is identifiable by a
        genuinely large gap from the start marker, not just any gap. 3000
        chars is comfortably larger than any TOC entry-to-entry span and
        comfortably smaller than a real Business section (tens of thousands
        of characters), so picking the first following end-marker past that
        threshold - rather than the nearest one, or always the farthest one
        (which risks overshooting past the real section into Risk
        Factors/Properties/etc on a filing with a later spurious match) -
        reliably separates the TOC from the real body.

        One more wrinkle, also confirmed on KEX: SEC's inline-tagged HTML
        occasionally splits a heading word in two once tags are stripped
        (the real heading came through as "Item 1. Busi ness", not
        "Business" - a stray space left behind by a tag boundary that used
        to sit mid-word). start_pattern tolerates that split; without it, the
        real heading's start position would never be found at all, and only
        the TOC's (unsplit) occurrence would be in `starts`, so the gap-based
        logic below would still select the TOC as the start - same bug,
        different cause. Once there are two valid start candidates (TOC and
        real), the real one is the LATEST start that still reaches a
        genuinely distant end marker - the TOC's start reaches that same end
        marker too (spanning a nominally larger range), but that range is
        mostly TOC noise, not real content.
        """
        import re
        from html import unescape

        # Remove HTML tags and decode entities
        text = re.sub(r'<[^>]+>', ' ', content)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()

        start_pattern = re.compile(r'item\s*1\.?\s*busi\s*ness', re.IGNORECASE)
        end_pattern = re.compile(r'item\s*1a\.?\s*risk\s*factors|item\s*2\.?\s*properties', re.IGNORECASE)
        TOC_GAP_THRESHOLD = 3000

        starts = [m.start() for m in start_pattern.finditer(text)]
        end_positions = [m.start() for m in end_pattern.finditer(text)]

        candidates = []
        for s in starts:
            qualifying_ends = [e for e in end_positions if e > s and e - s > TOC_GAP_THRESHOLD]
            if qualifying_ends:
                candidates.append((s, qualifying_ends[0]))

        best_start, best_end, best_len = None, None, 0
        if candidates:
            best_start, best_end = max(candidates, key=lambda pair: pair[0])
            best_len = best_end - best_start

        # A real Business section runs to thousands of characters; a TOC line
        # (title + page number) does not - 200 chars is a generous floor that
        # rejects TOC matches without risking rejecting a genuinely short
        # section.
        if best_start is not None and best_len > 200:
            # Full section, uncapped (see get_business_description docstring) -
            # bounded only as a sanity ceiling against a pathological match.
            return text[best_start:min(best_end, best_start + 200000)]

        # Fallback: look for business-related keywords
        business_keywords = ['products', 'services', 'operations', 'segments', 'revenue']
        for keyword in business_keywords:
            pattern = f'.*{keyword}.*'
            matches = re.findall(pattern, text[:10000], re.IGNORECASE)
            if matches:
                return ' '.join(matches[:3])  # First 3 relevant sentences

        return "Business description not found in filing"
    
    def get_segment_financials(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Real, filing-sourced per-segment revenue and profit, from both the
        latest 10-K (annual) and latest 10-Q (quarter) when available.

        get_segment_revenue_data below (the companyfacts-API-based method)
        can never return real per-segment numbers - confirmed directly: that
        API's data points have no 'segment' dimension key at all, only a
        NumberOfReportableSegments count. This method instead uses SEC's own
        rendered financial-statement reports (FilingSummary.xml -> the
        segment-detail R#.htm), which are pandas.read_html-parseable HTML
        tables - verified directly against KEX's real 10-K (R46.htm,
        "Operating Results by Segment (Details)"): Marine Transportation
        (KMT) $1,935,305K revenue / $374,458K pre-tax earnings, Distribution
        & Services $1,428,745K / $130,752K - a 57.5%/42.5% split, matching
        the real structure (our LLM-only estimate had been 78%/22% with the
        margins backwards).

        Each period's segments are labeled with their own source and period
        end date - annual and quarterly figures are never merged into one
        number silently.
        """
        result: Dict[str, Any] = {'ticker': ticker}
        annual = self._get_segment_financials_for_filing(ticker, self.get_latest_10k(ticker), '10-K')
        if annual:
            result['annual'] = annual
        quarterly = self._get_segment_financials_for_filing(ticker, self.get_latest_10q(ticker), '10-Q')
        if quarterly:
            result['quarterly'] = quarterly
        return result if ('annual' in result or 'quarterly' in result) else None

    def _get_segment_financials_for_filing(self, ticker: str, filing_data: Optional[Dict[str, Any]], source: str) -> Optional[Dict[str, Any]]:
        """Parse real per-segment financials out of one specific filing (a
        10-K or 10-Q) via its FilingSummary.xml -> segment-detail R#.htm."""
        if not filing_data:
            return None
        try:
            cik = self._get_cik(ticker)
            if not cik:
                return None
            dir_url = self._archive_dir_url(cik, filing_data)
            summary_resp = requests.get(f"{dir_url}/FilingSummary.xml", headers=self.headers)
            time.sleep(self.rate_limit_delay)
            if summary_resp.status_code != 200:
                debug_print(f"[SEC_DEBUG] No FilingSummary.xml for {ticker} {source}")
                return None

            candidates = self._rank_segment_report_candidates(summary_resp.text)
            for html_filename in candidates:
                report_resp = requests.get(f"{dir_url}/{html_filename}", headers=self.headers)
                time.sleep(self.rate_limit_delay)
                if report_resp.status_code != 200:
                    continue
                segments = self._parse_segment_report_table(report_resp.text)
                total_company_revenue = segments.pop('_total_company_revenue', None)
                segments_with_revenue = {name: data for name, data in segments.items() if data.get('revenue') is not None}
                if len(segments_with_revenue) < 2:
                    continue
                total_revenue = sum(d['revenue'] for d in segments_with_revenue.values())
                # Sanity gate against the table's own consolidated total - a
                # filer's nested sub-dimension (confirmed on ALTO: per-segment
                # product breakdowns render with the same "[Member]" pattern
                # as the real segment axis, with no other signal to tell them
                # apart) inflates this sum well past the real total. Rejecting
                # a bad parse and falling back is safer than returning a
                # structured-looking but wrong breakdown.
                if total_company_revenue and abs(total_revenue - total_company_revenue) / total_company_revenue > 0.15:
                    debug_print(f"[SEC_DEBUG] Rejecting {html_filename} for {ticker} {source}: segment sum {total_revenue} vs company total {total_company_revenue}")
                    continue
                return {
                    'source': source,
                    'filing_date': filing_data.get('filing_date'),
                    'accession_number': filing_data.get('accession_number'),
                    'report_file': html_filename,
                    'total_revenue': total_revenue,
                    'segments': segments_with_revenue,
                }
            debug_print(f"[SEC_DEBUG] No usable segment-detail report found for {ticker} {source} among {len(candidates)} candidates")
            return None
        except Exception as e:
            debug_print(f"[SEC_DEBUG] get_segment_financials failed for {ticker} {source}: {e}")
            return None

    def _rank_segment_report_candidates(self, filing_summary_xml: str) -> List[str]:
        """Return R#.htm filenames from a FilingSummary.xml, best-first, for
        the report most likely to be the per-segment operating-results
        detail table (there are usually several segment-related reports -
        a policy note, a tables shell, an overview, and the actual details -
        confirmed on KEX: 4 reports contain 'segment' in their ShortName,
        only one has the real per-member revenue/profit breakdown)."""
        import re as _re
        reports = _re.findall(r'<Report\b.*?</Report>', filing_summary_xml, _re.DOTALL)
        scored = []
        for r in reports:
            short = _re.search(r'<ShortName>(.*?)</ShortName>', r, _re.DOTALL)
            html = _re.search(r'<HtmlFileName>(.*?)</HtmlFileName>', r, _re.DOTALL)
            if not short or not html:
                continue
            short_lower = short.group(1).lower()
            if 'segment' not in short_lower:
                continue
            score = 0
            if 'detail' in short_lower:
                score += 2
            if any(kw in short_lower for kw in ['operating result', 'revenue', 'profit', 'financial information', 'operating segment']):
                score += 2
            if 'polic' in short_lower or 'table' in short_lower:
                score -= 2
            # Confirmed on ALTO: a report titled "...Total Assets by Operating
            # Segment..." also matches 'segment'+'detail' but only has asset
            # figures, no revenue/profit - rank it below plausible P&L tables.
            if 'asset' in short_lower and not any(kw in short_lower for kw in ['revenue', 'operating result', 'profit']):
                score -= 3
            scored.append((score, html.group(1)))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [html_filename for _, html_filename in scored]

    _AGGREGATE_MEMBER_NAMES = {'reportable segments', 'all other segments', 'total', 'consolidated'}

    def _parse_segment_report_table(self, html_text: str) -> Dict[str, Dict[str, Any]]:
        """Parse a SEC-rendered segment-detail report (an R#.htm financial
        statement table) into {member_name: {'revenue':, 'revenue_prior':,
        'profit':, 'profit_prior':, 'profit_measure':}}.

        These reports repeat the same line items once per segment member, as
        a run of rows: a "<Member Name> [Member]" header row, then that
        member's own line items until the next "[Member]" row. The aggregate
        "Reportable Segments [Member]" block (the sum across all members, not
        an individual one) is skipped - its own name is in
        _AGGREGATE_MEMBER_NAMES - so only real, individually named segments
        are returned.
        """
        import re as _re
        import pandas as pd
        from io import StringIO

        scale = 1000 if _re.search(r'in\s+Thousands', html_text, _re.IGNORECASE) else (
            1_000_000 if _re.search(r'in\s+Millions', html_text, _re.IGNORECASE) else 1
        )

        try:
            tables = pd.read_html(StringIO(html_text))
        except Exception:
            return {}
        if not tables:
            return {}
        t = tables[0]
        if t.shape[1] < 2:
            return {}

        # Not end-anchored: pandas.read_html flattens some rowspan'd header
        # cells into one string with multiple "[Member]" qualifiers (confirmed
        # on KEX: "KMT [Member] | Reportable Segments [Member]" is a SINGLE
        # cell) - only the first one is the actual segment name, the rest is
        # the same "which axis" qualifier repeated on every member's own row.
        member_pattern = _re.compile(r'^(.*?)\[Member\]', _re.IGNORECASE)
        # A profit/earnings measure is preferred in this priority order - the
        # company's own disclosed measure (e.g. "earnings before taxes on
        # income") over a generic one, matching how the filing itself frames
        # segment performance rather than imposing an external definition.
        profit_label_priority = [
            'earnings before taxes on income', 'segment profit', 'operating income',
            'income from operations', 'operating income loss', 'net income',
            'income (loss) before provision (benefit) for income taxes',
        ]
        # Revenue line-item wording varies by filer too - confirmed directly:
        # KEX uses "Revenues", ALTO uses "Net Sales".
        revenue_label_priority = [
            'revenues', 'revenue', 'net sales', 'net revenues', 'total revenue',
            'total revenues', 'total net sales', 'sales',
        ]

        segments: Dict[str, Dict[str, Any]] = {}
        pre_member_lines: Dict[str, List[float]] = {}
        seen_any_member = False
        current_member = None
        for i in range(len(t)):
            label_cell = t.iloc[i, 0]
            label = '' if pd.isna(label_cell) else str(label_cell).strip()
            m = member_pattern.match(label)
            if m:
                seen_any_member = True
                name = m.group(1).strip()
                if name.lower() in self._AGGREGATE_MEMBER_NAMES:
                    current_member = None
                else:
                    current_member = name
                    segments.setdefault(current_member, {'_lines': {}})
                continue
            if not label or '[Line Items]' in label:
                continue
            if current_member is None:
                if not seen_any_member:
                    # Rows before any "[Member]" row is seen are the
                    # consolidated/total-company figures (confirmed on both
                    # KEX and ALTO) - captured as the ground truth a parsed
                    # segment breakdown must sum close to, since a filer's
                    # nested sub-dimensions (e.g. ALTO's per-segment product
                    # breakdown) can otherwise masquerade as extra top-level
                    # segments with no other signal to catch them.
                    for col in range(1, t.shape[1]):
                        val = self._parse_money_cell(t.iloc[i, col])
                        if val is not None:
                            pre_member_lines.setdefault(label, []).append(val * scale)
                continue
            values = []
            for col in range(1, t.shape[1]):
                raw = t.iloc[i, col]
                val = self._parse_money_cell(raw)
                if val is not None:
                    values.append(val * scale)
            if values:
                # Keep the first value seen per label - a duplicate "[Member]"
                # entry style (confirmed on KEX: some filers emit a compact
                # single-line-item row before the full compound-header block
                # for the same member) repeats the same figure rather than a
                # different one, so first-seen is as good as any.
                segments[current_member]['_lines'].setdefault(label, values)

        result = {}
        for name, data in segments.items():
            lines = data['_lines']
            revenue_values = None
            for candidate in revenue_label_priority:
                for label, values in lines.items():
                    if label.lower() == candidate:
                        revenue_values = values
                        break
                if revenue_values:
                    break
            profit_label_used, profit_values = None, None
            for candidate in profit_label_priority:
                for label, values in lines.items():
                    if label.lower() == candidate:
                        profit_label_used, profit_values = label, values
                        break
                if profit_values:
                    break
            entry = {
                'revenue': revenue_values[0] if revenue_values else None,
                'revenue_prior': revenue_values[1] if revenue_values and len(revenue_values) > 1 else None,
                'profit': profit_values[0] if profit_values else None,
                'profit_prior': profit_values[1] if profit_values and len(profit_values) > 1 else None,
                'profit_measure': profit_label_used,
            }
            result[name] = entry

        total_company_revenue = None
        for candidate in revenue_label_priority:
            for label, values in pre_member_lines.items():
                if label.lower() == candidate and values:
                    total_company_revenue = values[0]
                    break
            if total_company_revenue is not None:
                break
        result['_total_company_revenue'] = total_company_revenue
        return result

    @staticmethod
    def _parse_money_cell(raw) -> Optional[float]:
        """Parse one table cell into a float, handling SEC's rendering
        conventions: parentheses for negative, $ and thousands separators,
        and blank/NaN cells."""
        import pandas as pd
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            return None
        text = str(raw).strip()
        if not text or text.lower() == 'nan':
            return None
        negative = text.startswith('(') and text.endswith(')')
        cleaned = text.strip('()').replace('$', '').replace(',', '').strip()
        if not cleaned or not _RE_NUMERIC.match(cleaned):
            return None
        value = float(cleaned)
        return -value if negative else value

    def get_segment_revenue_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Extract segment revenue and operating income data from SEC filings"""
        try:
            facts = self.get_filing_facts(ticker)
            if not facts or 'facts' not in facts:
                return None
            
            us_gaap = facts['facts'].get('us-gaap', {})
            
            # Look for segment-specific fields with dimension information
            segments = []
            total_revenue = 0
            total_operating_income = 0
            
            # Extract company totals first
            revenue_keys = ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues']
            for key in revenue_keys:
                if key in us_gaap and 'USD' in us_gaap[key].get('units', {}):
                    recent_data = sorted(us_gaap[key]['units']['USD'], key=lambda x: x.get('end', ''), reverse=True)[:1]
                    if recent_data:
                        total_revenue = recent_data[0].get('val', 0)
                        break
            
            operating_keys = ['OperatingIncomeLoss']
            for key in operating_keys:
                if key in us_gaap and 'USD' in us_gaap[key].get('units', {}):
                    recent_data = sorted(us_gaap[key]['units']['USD'], key=lambda x: x.get('end', ''), reverse=True)[:1]
                    if recent_data:
                        total_operating_income = recent_data[0].get('val', 0)
                        break
            
            # Look for segment-specific revenue fields - use actual XBRL field names
            segment_revenue_fields = [
                'SegmentReportingInformationRevenues',
                'SegmentReportingInformationOperatingIncomeLoss', 
                'SegmentReportingSegmentRevenues',
                'RevenueFromExternalCustomers',
                'SegmentRevenues'
            ]
            
            segment_income_fields = [
                'SegmentReportingInformationOperatingIncomeLoss',
                'SegmentReportingSegmentOperatingProfitLoss',
                'SegmentOperatingIncome'
            ]
            
            segment_data = {}
            
            debug_print(f"[SEC_DEBUG] Looking for segment data in {ticker}...")
            
            # Extract segment revenue data
            for field_name in segment_revenue_fields:
                if field_name in us_gaap:
                    debug_print(f"[SEC_DEBUG] Found field: {field_name}")
                    units = us_gaap[field_name].get('units', {})
                    if 'USD' in units:
                        debug_print(f"[SEC_DEBUG] USD data points: {len(units['USD'])}")
                        for i, data_point in enumerate(units['USD'][:3]):  # Check first 3
                            debug_print(f"[SEC_DEBUG] Data point {i}: keys = {list(data_point.keys())}")
                            if 'segment' in data_point:
                                debug_print(f"[SEC_DEBUG] Found segment: {data_point['segment']}")
                            else:
                                debug_print(f"[SEC_DEBUG] No segment dimension found")
            
            # Check if any segment fields exist at all
            segment_field_names = [f for f in us_gaap.keys() if any(kw in f.lower() for kw in ['segment', 'reportable'])]
            debug_print(f"[SEC_DEBUG] All segment fields: {segment_field_names[:5]}...")  # Show first 5
            
            # Extract segment revenue data
            for field_name in segment_revenue_fields:
                if field_name in us_gaap:
                    units = us_gaap[field_name].get('units', {})
                    if 'USD' in units:
                        for data_point in units['USD']:
                            # Look for segment dimension
                            if 'segment' in data_point:
                                segment_name = data_point['segment'].get('value', 'Unknown')
                                value = data_point.get('val', 0)
                                end_date = data_point.get('end', '')
                                
                                if segment_name not in segment_data:
                                    segment_data[segment_name] = {}
                                
                                if 'revenue' not in segment_data[segment_name] or end_date > segment_data[segment_name].get('revenue_date', ''):
                                    segment_data[segment_name]['revenue'] = value
                                    segment_data[segment_name]['revenue_date'] = end_date
            
            # Extract segment operating income data
            for field_name in segment_income_fields:
                if field_name in us_gaap:
                    units = us_gaap[field_name].get('units', {})
                    if 'USD' in units:
                        for data_point in units['USD']:
                            if 'segment' in data_point:
                                segment_name = data_point['segment'].get('value', 'Unknown')
                                value = data_point.get('val', 0)
                                end_date = data_point.get('end', '')
                                
                                if segment_name not in segment_data:
                                    segment_data[segment_name] = {}
                                
                                if 'operating_income' not in segment_data[segment_name] or end_date > segment_data[segment_name].get('income_date', ''):
                                    segment_data[segment_name]['operating_income'] = value
                                    segment_data[segment_name]['income_date'] = end_date
            
            # Build segments list
            for segment_name, data in segment_data.items():
                segment_revenue = data.get('revenue', 0)
                segment_income = data.get('operating_income')
                
                segment_info = {
                    'segment_name': segment_name,
                    'revenue': segment_revenue,
                    'revenue_percentage': (segment_revenue / total_revenue * 100) if total_revenue > 0 else 0
                }
                
                if segment_income is not None and segment_revenue > 0:
                    operating_margin = (segment_income / segment_revenue) * 100
                    segment_info['operating_income'] = segment_income
                    segment_info['operating_margin'] = round(operating_margin, 2)
                    
                    if operating_margin > 20:
                        segment_info['margin_profile'] = 'High'
                    elif operating_margin > 10:
                        segment_info['margin_profile'] = 'Medium'
                    else:
                        segment_info['margin_profile'] = 'Low'
                else:
                    segment_info['margin_profile'] = 'Unknown'
                
                segments.append(segment_info)
            
            # If no segment data found, return company-level data
            if not segments and total_revenue > 0:
                overall_margin = None
                margin_profile = 'Medium'
                
                if total_operating_income is not None and total_revenue > 0:
                    overall_margin = (total_operating_income / total_revenue) * 100
                    if overall_margin > 20:
                        margin_profile = 'High'
                    elif overall_margin > 10:
                        margin_profile = 'Medium'
                    else:
                        margin_profile = 'Low'
                
                segments = [{
                    'segment_name': 'Total Company',
                    'revenue': total_revenue,
                    'revenue_percentage': 100.0,
                    'operating_income': total_operating_income,
                    'operating_margin': round(overall_margin, 2) if overall_margin else None,
                    'margin_profile': margin_profile
                }]
            
            return {
                'ticker': ticker,
                'segment_data': {
                    'primary_segments': segments,
                    'total_revenue': total_revenue,
                    'total_operating_income': total_operating_income
                },
                'data_source': 'SEC EDGAR XBRL'
            }
            
        except Exception as e:
            debug_print(f"Error extracting segment data for {ticker}: {e}")
            return None