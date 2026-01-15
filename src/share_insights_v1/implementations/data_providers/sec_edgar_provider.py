import requests
import json
from typing import Dict, Any, Optional
from ...interfaces.sec_data_provider import SECDataProvider
import time
from ...utils.debug_printer import debug_print
class SECEdgarProvider(SECDataProvider):
    """SEC EDGAR API data provider for financial filings"""
    
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.cik_retrieval_url = "https://sec.gov"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
    
    def get_business_description(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get business description from latest 10-K filing"""
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
            
            # Construct URL to actual filing document - try multiple formats
            accession = filing_data['accession_number'].replace('-', '')
            primary_doc = filing_data['primary_document']
            
            # Try different URL formats that SEC uses
            possible_urls = [
                f"{self.base_url}/Archives/edgar/data/{cik}/{accession}/{primary_doc}",
                f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_doc}",
                f"{self.base_url}/Archives/edgar/data/{cik}/{filing_data['accession_number']}/{primary_doc}"
            ]
            
            content = None
            
            for doc_url in possible_urls:
                debug_print(f"[SEC_DEBUG] Trying URL: {doc_url}")
                response = requests.get(doc_url, headers=self.headers)
                time.sleep(self.rate_limit_delay)
                
                if response.status_code == 200:
                    content = response.text
                    debug_print(f"[SEC_DEBUG] Success with URL: {doc_url}")
                    break
                else:
                    debug_print(f"[SEC_DEBUG] Failed with status {response.status_code}: {doc_url}")
            
            if not content:
                debug_print(f"[SEC_DEBUG] All URL formats failed for {ticker}")
                return None
            
            debug_print(f"[SEC_DEBUG] Document fetched successfully, size: {len(content)} chars")
            business_section = self._extract_business_section(content)
            
            debug_print(f"[SEC_DEBUG] Business section extracted: {len(business_section)} chars")
            
            return {
                'ticker': ticker,
                'filing_date': filing_data['filing_date'],
                'business_description': business_section,
                'data_source': 'SEC 10-K Filing'
            }
            
        except Exception as e:
            debug_print(f"[SEC_DEBUG] Error fetching business description for {ticker}: {e}")
            import traceback
            traceback.debug_print_exc()
            return None
    
    def _extract_business_section(self, content: str) -> str:
        """Extract Item 1 - Business section from 10-K filing"""
        import re
        from html import unescape
        
        # Remove HTML tags and decode entities
        text = re.sub(r'<[^>]+>', ' ', content)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Look for Item 1 Business section
        patterns = [
            r'Item\s*1[\s\.].*?Business.*?(?=Item\s*1A|Item\s*2|$)',
            r'ITEM\s*1[\s\.].*?BUSINESS.*?(?=ITEM\s*1A|ITEM\s*2|$)',
            r'Part\s*I.*?Item\s*1.*?Business.*?(?=Item\s*1A|Item\s*2|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                business_text = match.group(0)
                # Limit to reasonable length (first 5000 chars)
                return business_text[:5000] if len(business_text) > 5000 else business_text
        
        # Fallback: look for business-related keywords
        business_keywords = ['products', 'services', 'operations', 'segments', 'revenue']
        for keyword in business_keywords:
            pattern = f'.*{keyword}.*'
            matches = re.findall(pattern, text[:10000], re.IGNORECASE)
            if matches:
                return ' '.join(matches[:3])  # First 3 relevant sentences
        
        return "Business description not found in filing"
    
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