from typing import Dict, Any
from ..interfaces.classifier import ICompanyClassifier
from ..models.company import CompanyType

class CompanyClassifier(ICompanyClassifier):
    """Company type classifier implementation"""
    
    def classify(self, ticker: str, metrics: Dict[str, Any]) -> str:
        """Classify company based on financial metrics"""
        
        try:

            market_cap = metrics.get('marketCap', 0)
            sector = metrics.get('sector', '')
            industry = metrics.get('industry', '')
            
            # Check for ETFs first
            fund_family = metrics.get('fundFamily', '')
            category = metrics.get('category', '')
            quote_type = metrics.get('quoteType', '')
            long_name = metrics.get('longName', '')

            # Enhanced ETF Detection
            etf_indicators = [
                quote_type == 'ETF',
                'ETF' in long_name.upper(),
                'FUND' in long_name.upper(),
                'TRUST' in long_name.upper(),
                bool(fund_family),
                bool(category),
                ticker.endswith('ETF'),
                # Common ETF tickers
                ticker in ['QQQ', 'SPY', 'IWM', 'VTI', 'VOO', 'SLV', 'GLD', 'TLT', 'EFA', 'EEM'],
                # ETF naming patterns
                any(pattern in ticker for pattern in ['SPDR', 'iShares', 'Vanguard']),
                # Check if total revenue is 0 (typical for ETFs)
                metrics.get('total_revenue') == 0 or None
            ]

            if any(etf_indicators):
                    return CompanyType.ETF
                
                # Get financial data
            net_income = metrics.get('net_income', 0)
            fcf = metrics.get('free_cash_flow', 0)
            # Classification logic
            if 'Real Estate' in sector or 'REIT' in industry:
                return CompanyType.REIT
            elif 'Financial' in sector or 'Bank' in industry:
                return CompanyType.FINANCIAL
            elif sector in ['Energy', 'Materials'] or 'Mining' in industry:
                return CompanyType.COMMODITY
            elif net_income <= 0 and fcf <= 0 and market_cap < 5e9:  # <$5B market cap
                return CompanyType.STARTUP_LOSS_MAKING
            elif net_income <= 0 or fcf <= 0:
                return CompanyType.TURNAROUND
            elif market_cap > 50e9:  # >$50B market cap
                return CompanyType.MATURE_PROFITABLE
            elif metrics.get('yearly_revenue_growth', 0) > 0.15:  # >15% revenue growth
                return CompanyType.GROWTH_PROFITABLE
            elif sector in ['Energy', 'Materials', 'Industrials']:
                return CompanyType.CYCLICAL
            else:
                return CompanyType.MATURE_PROFITABLE
                
        except Exception as e:
            print(f"classify_company():{str(e)}")
            return CompanyType.MATURE_PROFITABLE  # Default fallback