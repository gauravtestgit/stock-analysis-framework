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