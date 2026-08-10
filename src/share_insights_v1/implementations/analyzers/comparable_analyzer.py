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
            ebitda = metrics.get('ebitda', 0) or 0
            total_debt = metrics.get('total_debt', 0) or 0
            total_cash = metrics.get('total_cash', 0) or 0

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

            # Config-based "fair" multiples for this sector/industry/company-type/quality
            config_multiples = {
                'pe': params.get('pe_multiple', 18),
                'ps': params.get('ps_multiple', 2.5),
                'pb': params.get('pb_multiple', 2.0),
                'ev_ebitda': params.get('ev_ebitda_multiple', 12)
            }

            # Live peer data - blended into the target multiples below when available,
            # so the valuation reflects what comparable companies actually trade at
            # today rather than only a static config assumption
            market_cap = metrics.get('market_cap', 0) or 0
            market = metrics.get('market', '')
            peer_tickers, peer_averages = self._get_peer_data(ticker, sector, industry, market_cap, market)
            target_multiples, multiple_sources = self._blend_multiples(config_multiples, peer_averages)

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

            # EV/EBITDA valuation - implied enterprise value from the multiple, converted
            # back to an equity value per share via the net-debt bridge. EBITDA is missing
            # or negative for a lot of small-cap/AU-NZ names (same gap as book value above),
            # so this is expected to be skipped often rather than fail the whole analysis
            try:
                if ebitda > 0 and shares_outstanding > 0:
                    implied_enterprise_value = ebitda * target_multiples['ev_ebitda']
                    implied_equity_value = implied_enterprise_value - total_debt + total_cash
                    if implied_equity_value > 0:
                        fair_values['ev_ebitda_fair_value'] = implied_equity_value / shares_outstanding
            except TypeError:
                pass  # malformed ebitda/debt/cash data for this ticker; skip rather than fail the whole analysis

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

            confidence = self._determine_confidence(fair_values, multiple_sources)

            result = {
                'method': 'Comparable Analysis',
                'applicable': True,
                'target_multiples': target_multiples,
                'config_multiples': config_multiples,
                'multiple_sources': multiple_sources,
                'fair_values': fair_values,
                'predicted_price': avg_fair_value,
                'current_price': current_price,
                'upside_downside_pct': upside_downside,
                'recommendation': recommendation,
                'confidence': confidence,
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
                    'ev_ebitda_multiple': f"{target_multiples['ev_ebitda']:.1f}x",
                    'quality_adjustment': quality_grade
                }
            }

            return result

        except Exception as e:
            return {'error': str(e)}

    def _determine_confidence(self, fair_values: Dict[str, float], multiple_sources: Dict[str, str]) -> str:
        """Confidence reflects how much of the valuation rests on real peer data vs
        config-only defaults, rather than being a fixed label regardless of inputs.
        """
        if not fair_values:
            return 'Low'

        blended_count = sum(1 for source in multiple_sources.values() if source == 'config+peer_blend')

        if len(fair_values) == 1 and blended_count == 0:
            # A single fair-value method with no live peer confirmation at all
            return 'Low'
        if len(fair_values) >= 3 and blended_count >= 2:
            return 'High'
        return 'Medium'

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

    def _get_peer_data(self, ticker: str, sector: str, industry: str, market_cap: float = 0, market: str = '') -> Tuple[List[str], Dict[str, float]]:
        """Fetch live peer tickers and their averaged valuation/performance metrics"""
        try:
            peer_tickers = self.peer_provider.get_industry_peers(ticker, sector, industry, market_cap, market)
            if not peer_tickers:
                return [], {}

            peer_metrics = self.peer_provider.get_peer_metrics(peer_tickers)
            peer_averages = self._average_peer_metrics(peer_metrics)
            return peer_tickers, peer_averages
        except Exception:
            return [], {}

    # Valuation ratios yfinance occasionally returns nonsensically for foreign
    # ADR/OTC listings (e.g. price-to-sales near 0, negative EV/EBITDA) - likely
    # a currency/share-basis mismatch on Yahoo's side rather than a real quote.
    # Bounding here (rather than excluding those peers/exchanges outright) keeps
    # legitimate small-cap/OTC peers in the set while dropping just the bad numbers.
    _PLAUSIBLE_RANGES = {
        'pe_ratio': (1, 500),
        'ev_ebitda': (1, 200),
        'price_to_sales': (0.1, 100),
        'price_to_book': (0.1, 100),
    }

    def _average_peer_metrics(self, peer_metrics: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate average metrics across peers (uses YahooPeerProvider's field names)"""
        averages = {}
        fields = ['pe_ratio', 'ev_ebitda', 'price_to_sales', 'price_to_book', 'roe', 'revenue_growth', 'profit_margin']

        for field in fields:
            values = [d.get(field) for d in peer_metrics.values() if d.get(field) is not None]
            bounds = self._PLAUSIBLE_RANGES.get(field)
            if bounds:
                values = [v for v in values if bounds[0] <= v <= bounds[1]]
            if values:
                averages[field] = sum(values) / len(values)

        return averages

    def _blend_multiples(self, config_multiples: Dict[str, float], peer_averages: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, str]]:
        """Blend static config target multiples with live peer-observed averages.

        Falls back to the config value alone for any multiple where peer data
        isn't available (e.g. thin/no industry peer coverage, or a peer fetch
        failure) - this mirrors how P/E, P/S, P/B already degrade gracefully
        elsewhere in this analyzer when an input is missing.
        """
        # target multiple key -> matching field name in peer_averages
        peer_key_map = {'pe': 'pe_ratio', 'ps': 'price_to_sales', 'pb': 'price_to_book', 'ev_ebitda': 'ev_ebitda'}

        blended = dict(config_multiples)
        sources = {key: 'config_only' for key in config_multiples}

        for target_key, peer_key in peer_key_map.items():
            peer_val = peer_averages.get(peer_key)
            if peer_val is not None and peer_val > 0:
                blended[target_key] = (config_multiples[target_key] + peer_val) / 2
                sources[target_key] = 'config+peer_blend'

        return blended, sources

    @staticmethod
    def _to_finite_float(value: Any) -> Optional[float]:
        """Coerce to a finite float, treating non-numeric or +/-inf/NaN values
        (e.g. yfinance's literal 'Infinity' string for an undefined ratio) as
        missing data rather than a value to compare against.
        """
        try:
            result = float(value)
        except (TypeError, ValueError):
            return None
        if result != result or result in (float('inf'), float('-inf')):  # NaN check + inf check
            return None
        return result

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
            # yfinance sometimes reports an undefined ratio as the literal string
            # 'Infinity' rather than a number (seen on DRO.AX's pe_ratio) - coerce
            # to a finite float so this crashes into "skip" rather than a raw
            # str-vs-float comparison error
            target_val = self._to_finite_float(target_metrics.get(target_key))
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
            target_val = self._to_finite_float(target_metrics.get(metric))
            peer_val = peer_avg.get(metric)
            # financial_metrics stores profit_margin as a percentage (e.g. 27.6) while
            # YahooPeerProvider's peer_avg is a raw fraction (e.g. 0.276) - normalize
            # to the same scale before comparing, or the target reads as "Superior"
            # on this metric almost every time regardless of actual performance
            if metric == 'profit_margin' and target_val is not None:
                target_val = target_val / 100
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
