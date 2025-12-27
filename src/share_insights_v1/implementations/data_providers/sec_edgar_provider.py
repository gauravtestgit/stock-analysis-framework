import requests
import json
from typing import Dict, Any, Optional
from ...interfaces.sec_data_provider import SECDataProvider
import time

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
            print(f"Error fetching 10-K for {ticker}: {e}")
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
            print(f"Error fetching 10-Q for {ticker}: {e}")
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
            print(f"Error fetching facts for {ticker}: {e}")
            return None
    
    def _get_cik(self, ticker: str) -> Optional[int]:
        """Get CIK number for ticker"""
        try:
            # Use SEC company tickers endpoint
            tickers_url = f"{self.cik_retrieval_url}/files/company_tickers.json"
            response = requests.get(tickers_url, headers=self.headers)
            time.sleep(self.rate_limit_delay)
            
            if response.status_code != 200:
                print(f"Failed to fetch tickers: {response.status_code}")
                return None
            
            data = response.json()
            
            # Search through the numbered entries
            for entry in data.values():
                if entry.get('ticker', '').upper() == ticker.upper():
                    return entry.get('cik_str')
            
            return None
            
        except Exception as e:
            print(f"Error getting CIK for {ticker}: {e}")
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
    
    def get_segment_revenue_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Extract segment revenue data from SEC filings"""
        try:
            facts = self.get_filing_facts(ticker)
            if not facts or 'facts' not in facts:
                return None
            
            # Extract segment data from XBRL facts
            us_gaap = facts['facts'].get('us-gaap', {})
            dei = facts['facts'].get('dei', {})
            
            segment_data = {
                'primary_segments': [],
                'revenue_diversification': 'Medium',
                'total_revenue': 0
            }
            
            # Look for segment revenue items
            segment_keys = [
                'RevenueFromContractWithCustomerIncludingAssessedTax',
                'Revenues', 'RevenueFromContractWithCustomer',
                'SegmentReporting', 'RevenueFromExternalCustomers'
            ]
            
            for key in segment_keys:
                if key in us_gaap:
                    units = us_gaap[key].get('units', {})
                    if 'USD' in units:
                        recent_data = sorted(units['USD'], key=lambda x: x.get('end', ''), reverse=True)[:3]
                        if recent_data:
                            segment_data['total_revenue'] = recent_data[0].get('val', 0)
                            break
            
            # Extract entity name for context
            entity_name = dei.get('EntityRegistrantName', {}).get('units', {}).get('shares', [{}])[0].get('val', ticker)
            
            return {
                'ticker': ticker,
                'entity_name': entity_name,
                'segment_data': segment_data,
                'data_source': 'SEC EDGAR XBRL'
            }
            
        except Exception as e:
            print(f"Error extracting segment data for {ticker}: {e}")
            return None