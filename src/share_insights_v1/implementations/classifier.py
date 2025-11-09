import json
import os
from typing import Dict, Any
from ..interfaces.classifier import ICompanyClassifier
from ..models.company import CompanyType

class CompanyClassifier(ICompanyClassifier):
    """Company type classifier implementation with JSON config"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load classification configuration from JSON file"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'classification_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading classification config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Fallback configuration if JSON file fails to load"""
        return {
            "company_types": {
                "REIT": {"sectors": ["Real Estate"], "industries": ["REIT"]},
                "FINANCIAL": {"sectors": ["Financial"], "industries": ["Banks"]},
                "COMMODITY": {"sectors": ["Energy", "Materials"], "industries": ["Mining"]},
                "CYCLICAL": {"sectors": ["Industrials"], "industries": ["Semiconductors"]}
            },
            "thresholds": {
                "startup_market_cap": 5e9,
                "mature_market_cap": 50e9,
                "growth_revenue_threshold": 0.15,
                "cyclical_growth_cap": 0.25
            },
            "etf_tickers": ["QQQ", "SPY", "IWM"],
            "etf_patterns": ["SPDR", "iShares"]
        }
    
    def _matches_company_type(self, company_type: str, sector: str, industry: str) -> bool:
        """Check if sector/industry matches a company type"""
        type_config = self.config["company_types"].get(company_type, {})
        return (sector in type_config.get("sectors", []) or 
                industry in type_config.get("industries", []))
    
    def classify(self, ticker: str, metrics: Dict[str, Any]) -> str:
        """Classify company based on financial metrics"""
        
        try:

            market_cap = metrics.get('market_cap', 0)
            sector = metrics.get('sector', '')
            industry = metrics.get('industry', '')
            
            # Check for ETFs first
            fund_family = metrics.get('fund_family', '')
            category = metrics.get('category', '')
            quote_type = metrics.get('quote_type', '')
            long_name = metrics.get('long_name', '')

            # Enhanced ETF Detection using config
            etf_indicators = [
                quote_type == 'ETF',
                'ETF' in long_name.upper(),
                'FUND' in long_name.upper(),
                'TRUST' in long_name.upper(),
                bool(fund_family),
                bool(category),
                ticker.endswith('ETF'),
                ticker in self.config.get('etf_tickers', []),
                any(pattern in ticker for pattern in self.config.get('etf_patterns', [])),
                (quote_type == 'ETF' and metrics.get('total_revenue', 0) == 0)
            ]

            if any(etf_indicators):
                    return CompanyType.ETF
                
                # Get financial data and thresholds
            net_income = metrics.get('net_income', 0)
            fcf = metrics.get('free_cash_flow', 0)
            revenue_growth = metrics.get('yearly_revenue_growth', 0)
            
            thresholds = self.config['thresholds']
            startup_cap = thresholds['startup_market_cap']
            mature_cap = thresholds['mature_market_cap']
            growth_threshold = thresholds['growth_revenue_threshold']
            cyclical_cap = thresholds['cyclical_growth_cap']
            
            # Classification logic using config
            if self._matches_company_type('REIT', sector, industry):
                return CompanyType.REIT
            elif self._matches_company_type('FINANCIAL', sector, industry):
                return CompanyType.FINANCIAL
            elif self._matches_company_type('COMMODITY', sector, industry):
                return CompanyType.COMMODITY
            elif net_income <= 0 and fcf <= 0 and market_cap < startup_cap:
                return CompanyType.STARTUP_LOSS_MAKING
            elif net_income <= 0 or fcf <= 0:
                return CompanyType.TURNAROUND
            elif self._matches_company_type('CYCLICAL', sector, industry) and revenue_growth <= cyclical_cap:
                return CompanyType.CYCLICAL
            elif market_cap > mature_cap and revenue_growth < growth_threshold:
                return CompanyType.MATURE_PROFITABLE
            elif revenue_growth >= growth_threshold:
                return CompanyType.GROWTH_PROFITABLE
            else:
                return CompanyType.MATURE_PROFITABLE
                
        except Exception as e:
            print(f"classify_company():{str(e)}")
            return CompanyType.MATURE_PROFITABLE  # Default fallback