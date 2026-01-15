from typing import Dict, Any, Optional, List
from ...interfaces.analyzer import IAnalyzer
from ...models.company import CompanyType
from ...config.config import FinanceConfig
import yfinance as yf

class ComparableAnalyzer(IAnalyzer):
    """Enhanced comparable company analysis with live peer data"""
    
    def __init__(self, config: Optional[FinanceConfig] = None):
        self.config = config if config is not None else FinanceConfig()
        
        # Industry peer mappings
        self.industry_peers = {
            'Consumer Electronics': ['AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN'],
            'Software - Application': ['MSFT', 'ORCL', 'CRM', 'ADBE', 'NOW'],
            'Semiconductors': ['NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO'],
            'Biotechnology': ['GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX'],
            'Banks - Regional': ['JPM', 'BAC', 'WFC', 'C', 'USB'],
            'Auto Manufacturers': ['TSLA', 'F', 'GM', 'TM', 'HMC'],
            'Entertainment': ['NFLX', 'DIS', 'CMCSA', 'WBD', 'PARA'],
            'Drug Manufacturers - Specialty & Generic': ['PFE', 'JNJ', 'MRK', 'LLY', 'ABBV']
        }
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comparable company analysis"""
        try:
            metrics = data.get('financial_metrics', {})
            company_info = data.get('company_info', {})
            
            # Financial metrics
            total_revenue = metrics.get('total_revenue', 0)
            net_income = metrics.get('net_income', 0)
            shares_outstanding = metrics.get('shares_outstanding', 0)
            current_price = metrics.get('current_price', 0)
            
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')
            quality_grade = data.get('quality_grade', 'C')
            company_type = data.get('company_type', CompanyType.MATURE_PROFITABLE)
            
            # Get industry-specific multiples from config
                        
            params = self.config.get_adjusted_parameters(
                sector=sector, 
                industry=industry,
                company_type=company_type, 
                quality_grade=quality_grade
            )
            
            # Extract target multiples
            target_multiples = {
                'pe': params.get('pe_multiple', 18),
                'ps': params.get('ps_multiple', 2.5),
                'pb': params.get('pb_multiple', 2.0),
                'ev_ebitda': params.get('ev_ebitda_multiple', 12)
            }
            
            # Calculate fair values using different multiples
            fair_values = {}
            
            # P/E valuation
            if net_income > 0 and shares_outstanding > 0:
                eps = net_income / shares_outstanding
                fair_values['pe_fair_value'] = eps * target_multiples['pe']
            
            # P/S valuation
            if total_revenue > 0 and shares_outstanding > 0:
                revenue_per_share = total_revenue / shares_outstanding
                fair_values['ps_fair_value'] = revenue_per_share * target_multiples['ps']
            
            # Calculate average fair value
            valid_values = [v for v in fair_values.values() if v > 0]
            avg_fair_value = sum(valid_values) / len(valid_values) if valid_values else 0
            
            # Reality check for distressed companies
            if company_type == CompanyType.TURNAROUND and quality_grade in ['D', 'F']:
                # Cap fair value at 3x current price for severely distressed companies
                max_reasonable_value = current_price * 3
                if avg_fair_value > max_reasonable_value:
                    avg_fair_value = max_reasonable_value
            
            # Calculate upside/downside
            upside_downside = 0
            if current_price > 0 and avg_fair_value > 0:
                upside_downside = ((avg_fair_value - current_price) / current_price) * 100
            
            # Get live peer analysis
            peer_analysis = None
            # peer_analysis = self._get_peer_analysis(ticker, sector, industry)
            
            # Generate recommendation
            recommendation = self._generate_recommendation(upside_downside)
            
            result = {
                'method': 'Comparable Analysis',
                'applicable': True,
                'target_multiples': target_multiples,
                'fair_values': fair_values,
                'predicted_price': avg_fair_value,
                'current_price': current_price,
                'upside_downside_pct': upside_downside,
                'recommendation': recommendation,
                'confidence': 'Medium',
                'sector': sector,
                'industry': industry,
                'parameters_used': {
                    'pe_multiple': f"{target_multiples['pe']:.1f}x",
                    'ps_multiple': f"{target_multiples['ps']:.1f}x",
                    'quality_adjustment': quality_grade
                }
            }
            
            # Add peer analysis if available
            if peer_analysis:
                result.update(peer_analysis)
            
            return result
            
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_recommendation(self, upside_downside: float) -> str:
        """Generate recommendation based on upside/downside"""
        if upside_downside > 25:
            return "Strong Buy"
        elif upside_downside > 10:
            return "Buy"
        elif upside_downside < -25:
            return "Strong Sell"
        elif upside_downside < -10:
            return "Sell"
        else:
            return "Hold"
    
    def _get_peer_analysis(self, ticker: str, sector: str, industry: str) -> Optional[Dict[str, Any]]:
        """Get live peer comparison data"""
        try:
            # Get peer tickers
            peer_tickers = self.industry_peers.get(industry, [])
            peer_tickers = [p for p in peer_tickers if p != ticker][:4]  # Top 4 peers
            
            if not peer_tickers:
                return None
            
            # Get peer metrics
            peer_data = {}
            for peer_ticker in peer_tickers:
                try:
                    stock = yf.Ticker(peer_ticker)
                    info = stock.info
                    peer_data[peer_ticker] = {
                        'pe_ratio': info.get('trailingPE'),
                        'ps_ratio': info.get('priceToSalesTrailing12Months'),
                        'pb_ratio': info.get('priceToBook'),
                        'ev_ebitda': info.get('enterpriseToEbitda'),
                        'roe': info.get('returnOnEquity'),
                        'profit_margin': info.get('profitMargins')
                    }
                except:
                    continue
            
            if not peer_data:
                return None
            
            # Calculate peer averages
            peer_averages = self._calculate_peer_averages(peer_data)
            
            # Get target company current multiples
            target_multiples = self._get_current_multiples(ticker)
            
            # Calculate relative position
            relative_position = self._calculate_relative_position(target_multiples, peer_averages)
            
            return {
                'peer_tickers': peer_tickers,
                'peer_averages': peer_averages,
                'current_multiples': target_multiples,
                'relative_position': relative_position,
                'peer_insights': self._generate_peer_insights(relative_position)
            }
            
        except Exception as e:
            print(f"Error in peer analysis: {e}")
            return None
    
    def _calculate_peer_averages(self, peer_data: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate average metrics across peers"""
        averages = {}
        metrics = ['pe_ratio', 'ps_ratio', 'pb_ratio', 'ev_ebitda', 'roe', 'profit_margin']
        
        for metric in metrics:
            values = [data.get(metric) for data in peer_data.values() if data.get(metric) is not None]
            if values:
                averages[metric] = sum(values) / len(values)
        
        return averages
    
    def _get_current_multiples(self, ticker: str) -> Dict[str, float]:
        """Get current multiples for target company"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                'pe_ratio': info.get('trailingPE'),
                'ps_ratio': info.get('priceToSalesTrailing12Months'),
                'pb_ratio': info.get('priceToBook'),
                'ev_ebitda': info.get('enterpriseToEbitda'),
                'roe': info.get('returnOnEquity'),
                'profit_margin': info.get('profitMargins')
            }
        except:
            return {}
    
    def _calculate_relative_position(self, target: Dict[str, float], peer_avg: Dict[str, float]) -> Dict[str, str]:
        """Calculate relative position vs peers"""
        position = {}
        
        # For valuation metrics (lower is better)
        for metric in ['pe_ratio', 'ps_ratio', 'pb_ratio', 'ev_ebitda']:
            target_val = target.get(metric)
            peer_val = peer_avg.get(metric)
            
            if target_val and peer_val:
                if target_val < peer_val * 0.9:
                    position[metric] = "Discount"
                elif target_val > peer_val * 1.1:
                    position[metric] = "Premium"
                else:
                    position[metric] = "Inline"
        
        # For performance metrics (higher is better)
        for metric in ['roe', 'profit_margin']:
            target_val = target.get(metric)
            peer_val = peer_avg.get(metric)
            
            if target_val and peer_val:
                if target_val > peer_val * 1.1:
                    position[metric] = "Superior"
                elif target_val < peer_val * 0.9:
                    position[metric] = "Below"
                else:
                    position[metric] = "Inline"
        
        return position
    
    def _generate_peer_insights(self, relative_position: Dict[str, str]) -> List[str]:
        """Generate insights from peer comparison"""
        insights = []
        
        # Valuation insights
        discount_count = sum(1 for pos in relative_position.values() if pos == "Discount")
        if discount_count >= 2:
            insights.append("Trading at discount to peer group")
        
        premium_count = sum(1 for pos in relative_position.values() if pos == "Premium")
        if premium_count >= 2:
            insights.append("Trading at premium to peer group")
        
        # Performance insights
        if relative_position.get('roe') == "Superior" and relative_position.get('profit_margin') == "Superior":
            insights.append("Superior profitability vs peers")
        elif relative_position.get('roe') == "Below" or relative_position.get('profit_margin') == "Below":
            insights.append("Underperforming peers on profitability")
        
        return insights
    
    def is_applicable(self, company_type: str) -> bool:
        """Comparable analysis applies to most company types except ETFs"""
        excluded_types = [CompanyType.ETF.value]
        return company_type not in excluded_types