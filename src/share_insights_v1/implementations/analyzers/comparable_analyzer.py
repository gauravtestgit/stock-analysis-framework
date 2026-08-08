from typing import Dict, Any, Optional, List, Tuple
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.peer_comparison_provider import PeerComparisonProvider
from ...models.company import CompanyType
from ...config.config import FinanceConfig
from ...implementations.data_providers.yahoo_peer_provider import YahooPeerProvider

class ComparableAnalyzer(IAnalyzer):
    """Comparable company analysis using sector-target multiples plus live peer data"""

    def __init__(self, config: Optional[FinanceConfig] = None, peer_provider: Optional[PeerComparisonProvider] = None):
        self.config = config if config is not None else FinanceConfig()
        # Reuses the shared peer-data abstraction instead of hand-rolling yfinance
        # calls here; defaults to the real provider but is injectable for tests
        self.peer_provider = peer_provider or YahooPeerProvider()

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
            # yfinance sometimes includes 'bookValue' as an explicit None rather than
            # omitting it, so .get(key, 0) alone won't catch that - normalize with `or 0`
            book_value_per_share = metrics.get('book_value_per_share', 0) or 0

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

            # Live peer data - informational for now (relative position vs peers);
            # does not yet affect target_multiples/fair_values below
            peer_tickers, peer_averages = self._get_peer_data(ticker, sector, industry)

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

            # P/B valuation - book value isn't available for a lot of stocks, so this
            # is expected to be skipped often; that's fine, it just won't contribute
            # to the average fair value below (same as P/E and P/S when unavailable)
            try:
                if book_value_per_share > 0:
                    fair_values['pb_fair_value'] = book_value_per_share * target_multiples['pb']
            except TypeError:
                pass  # malformed book value data for this ticker; skip P/B rather than fail the whole analysis

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

            # Generate recommendation
            recommendation = self._generate_recommendation(upside_downside)

            # Relative position vs live peers (Discount/Premium/Inline, Superior/Below) -
            # uses the target's own current multiples, already present in financial_metrics,
            # rather than re-fetching them with a second yfinance call
            relative_position = {}
            peer_insights = []
            if peer_averages:
                relative_position = self._calculate_relative_position(metrics, peer_averages)
                peer_insights = self._generate_peer_insights(relative_position)

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
                'peer_tickers': peer_tickers,
                'peer_averages': peer_averages,
                'relative_position': relative_position,
                'peer_insights': peer_insights,
                'parameters_used': {
                    'pe_multiple': f"{target_multiples['pe']:.1f}x",
                    'ps_multiple': f"{target_multiples['ps']:.1f}x",
                    'pb_multiple': f"{target_multiples['pb']:.1f}x",
                    'quality_adjustment': quality_grade
                }
            }

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

    def _get_peer_data(self, ticker: str, sector: str, industry: str) -> Tuple[List[str], Dict[str, float]]:
        """Fetch live peer tickers and their averaged valuation/performance metrics"""
        try:
            peer_tickers = self.peer_provider.get_industry_peers(ticker, sector, industry)
            if not peer_tickers:
                return [], {}

            peer_metrics = self.peer_provider.get_peer_metrics(peer_tickers)
            peer_averages = self._average_peer_metrics(peer_metrics)
            return peer_tickers, peer_averages
        except Exception:
            return [], {}

    def _average_peer_metrics(self, peer_metrics: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate average metrics across peers (uses YahooPeerProvider's field names)"""
        averages = {}
        fields = ['pe_ratio', 'ev_ebitda', 'price_to_sales', 'price_to_book', 'roe', 'revenue_growth', 'profit_margin']

        for field in fields:
            values = [d.get(field) for d in peer_metrics.values() if d.get(field) is not None]
            if values:
                averages[field] = sum(values) / len(values)

        return averages

    def _calculate_relative_position(self, target_metrics: Dict[str, Any], peer_avg: Dict[str, float]) -> Dict[str, str]:
        """Calculate the target's relative position vs peer averages"""
        position = {}

        # For valuation metrics (lower is better) - target field name -> peer field name,
        # since financial_metrics and YahooPeerProvider don't share identical naming
        valuation_metrics = [
            ('pe_ratio', 'pe_ratio'),
            ('ps_ratio', 'price_to_sales'),
            ('pb_ratio', 'price_to_book'),
        ]
        for target_key, peer_key in valuation_metrics:
            target_val = target_metrics.get(target_key)
            peer_val = peer_avg.get(peer_key)
            # Explicit None checks rather than truthy checks - a legitimate 0.0 value
            # (e.g. breakeven) shouldn't be silently treated as missing data
            if target_val is not None and peer_val:
                if target_val < peer_val * 0.9:
                    position[peer_key] = "Discount"
                elif target_val > peer_val * 1.1:
                    position[peer_key] = "Premium"
                else:
                    position[peer_key] = "Inline"

        # For performance metrics (higher is better)
        for metric in ['roe', 'profit_margin']:
            target_val = target_metrics.get(metric)
            peer_val = peer_avg.get(metric)
            if target_val is not None and peer_val:
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
