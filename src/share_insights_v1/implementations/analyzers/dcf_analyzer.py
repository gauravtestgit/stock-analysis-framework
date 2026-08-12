from typing import Dict, Any, Optional
from ...interfaces.analyzer import IAnalyzer
from ...models.company import CompanyType
from ..calculators import dcf_yf_new as dcf_yf
from ...config.config import FinanceConfig
from ...utils.debug_printer import debug_print

class DCFAnalyzer(IAnalyzer):
    """DCF valuation analyzer implementation using original dcf_yf logic.

    Computes a Base Case (identical to the original single-scenario behavior)
    plus a few automatic alternative scenarios (Bull/Bear/Rate Shock), and an
    optional user-supplied Custom scenario if overrides are provided via
    data['dcf_overrides']. Top-level result fields always reflect the Base
    Case, unchanged - scenarios are nested under result['scenarios'].
    """

    def __init__(self, config : Optional[FinanceConfig] = None):
        self.config = config if config is not None else FinanceConfig()

    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform DCF analysis using original dcf_yf functions"""
        try:
            company_info = data.get('company_info', {})
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')
            quality_grade = data.get('quality_grade', 'C')
            company_type = data.get('company_type', CompanyType.MATURE_PROFITABLE)
            metrics = data.get('financial_metrics', {})
            # Get adjusted parameters from config
            params = self.config.get_adjusted_parameters(
                sector=sector,
                industry=industry,
                company_type=company_type,
                quality_grade=quality_grade
            )

            # Create temporary config with adjusted parameters
            base_tmp_config = FinanceConfig()
            base_tmp_config.use_default_ebitda_multiple = True
            base_tmp_config.default_ev_ebitda_multiple = params.get('ev_ebitda_multiple', base_tmp_config.default_ev_ebitda_multiple)
            base_tmp_config.max_cagr_threshold = params.get('max_cagr', base_tmp_config.max_cagr_threshold)
            base_tmp_config.default_terminal_growth = params.get('terminal_growth', base_tmp_config.default_terminal_growth)

            # Pass company type for risk adjustments
            base_tmp_config.company_type = company_type

            # Build the ticker once and reuse it across every scenario run below -
            # yfinance lazily caches .info/.cashflow/.income_stmt per-instance, so
            # this avoids re-fetching the same data 4-5x for one analysis
            import yfinance as yf
            ticker_obj = yf.Ticker(ticker)

            base = self._run_scenario(
                ticker, ticker_obj, base_tmp_config, metrics, company_type,
                sector, industry, quality_grade, overrides={}
            )

            scenarios = {'base_case': base}
            scenarios.update(self._run_preset_scenarios(
                ticker, ticker_obj, base_tmp_config, metrics, company_type,
                sector, industry, quality_grade, base
            ))

            dcf_overrides = data.get('dcf_overrides')
            if dcf_overrides:
                try:
                    custom_cfg = base_tmp_config.with_overrides(**dcf_overrides)
                    scenarios['custom'] = self._run_scenario(
                        ticker, ticker_obj, custom_cfg, metrics, company_type,
                        sector, industry, quality_grade, overrides=dcf_overrides
                    )
                except Exception as e:
                    scenarios['custom'] = {'error': str(e)}

            # Top-level fields are exactly the Base Case's, unchanged from before
            # this scenario support was added - only the new 'scenarios' key is additive
            result = dict(base)
            result['scenarios'] = scenarios
            return result

        except Exception as e:
            return {'error': str(e)}

    def _run_preset_scenarios(self, ticker: str, ticker_obj, base_tmp_config: FinanceConfig,
                             metrics: Dict[str, Any], company_type, sector: str, industry: str,
                             quality_grade: str, base: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Compute the automatic Bull/Bear/Rate-Shock scenarios. Each runs independently
        so one failing doesn't affect the Base Case or the others."""
        base_rf = base.get('dcf_calculations', {}).get('risk_free_rate')

        preset_overrides = {
            # A much higher growth ceiling (still capped, not unbounded - a fully
            # open cap risks one data anomaly producing a non-credible number) so
            # real historical CAGR flows through for hypergrowth names that the
            # base sector/quality cap would otherwise clamp far below their actual
            # trajectory
            'bull_high_growth': {
                'max_cagr_threshold': 0.75,
            },
            # Tighter growth, lower terminal growth, and this is the scenario that
            # actually exercises the terminal-value dominance cap
            'bear': {
                'max_cagr_threshold': max(base_tmp_config.max_cagr_threshold * 0.5, 0.02),
                'default_terminal_growth': max(base_tmp_config.default_terminal_growth - 0.010, 0.005),
                'max_terminal_value_ratio': 0.85,
            },
            # Isolates Fed-move sensitivity - growth assumptions untouched. Shifts
            # market_return by the same amount as risk_free_rate, holding the
            # equity risk premium constant: with cost_equity = rf + beta*(market_return-rf),
            # shifting rf alone changes cost_equity by (1-beta) per unit shift, which
            # goes NEGATIVE for beta > 1 (common for growth/tech names) - i.e. a rate
            # HIKE would paradoxically lower the discount rate and raise the price.
            # Shifting both by the same delta makes the sensitivity exactly 1
            # regardless of beta, so "higher rates" always means "lower valuation".
            'rate_shock_100bps': {
                'risk_free_rate_override': (base_rf + 0.01) if base_rf is not None else None,
                'market_return': base_tmp_config.market_return + 0.01,
            },
            # Uses analyst next-year consensus growth (from earnings_estimate /
            # revenue_estimate) instead of historical CAGR - a genuinely different
            # signal (forward Wall Street consensus vs. backward realized trend),
            # not just a different cap on the same historical number. Falls back
            # to the identical Base Case behavior per-metric when analyst coverage
            # is thin or unavailable (see GrowthCalculator._get_forward_guidance_growth),
            # so max_cagr_threshold is deliberately left at the Base Case value.
            'forward_guidance': {
                'use_forward_guidance_growth': True,
            },
        }

        results = {}
        for name, overrides in preset_overrides.items():
            try:
                cfg = base_tmp_config.with_overrides(**overrides)
                results[name] = self._run_scenario(
                    ticker, ticker_obj, cfg, metrics, company_type,
                    sector, industry, quality_grade, overrides=overrides
                )
            except Exception as e:
                debug_print(f"DCF scenario '{name}' failed for {ticker}: {e}")
                results[name] = {'error': str(e)}
        return results

    def _run_scenario(self, ticker: str, ticker_obj, cfg: FinanceConfig, metrics: Dict[str, Any],
                     company_type, sector: str, industry: str, quality_grade: str,
                     overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Run one DCF scenario against an adjusted config and shape the result -
        this is the exact logic the analyzer always ran, now reusable per-scenario."""
        dcf_calcuations = dcf_yf.get_share_price(ticker_symbol=ticker, config=cfg, ticker=ticker_obj)
        share_price = dcf_calcuations.get('share_price', 0)
        equity_value = dcf_calcuations.get('equity_value', 0)

        current_price = metrics.get('current_price', 0)

        if current_price > 0:
            upside_downside = ((share_price - current_price) / current_price) * 100
        else:
            upside_downside = 0

        # Apply valuation discount if applicable
        valuation_discount = self.config.company_type_adjustments.get(
            company_type, {}
        ).get('valuation_discount', 0.0)

        if valuation_discount > 0:
            share_price *= (1 - valuation_discount)
            upside_downside = ((share_price - current_price) / current_price) * 100 if current_price > 0 else 0

        recommendation = self._generate_recommendation(upside_downside)

        return {
            'method': 'DCF Analysis',
            'applicable': True,
            'predicted_price': share_price,
            'current_price': current_price,
            'upside_downside_pct': upside_downside,
            'total_equity_value': equity_value,
            'confidence': 'High' if company_type == CompanyType.MATURE_PROFITABLE else 'Medium',
            'valuation': 'Undervalued' if upside_downside > 20 else 'Overvalued' if upside_downside < -20 else 'Fair Value',
            'recommendation': recommendation,
            'dcf_calculations': dcf_calcuations,
            'parameters_used': {
                'max_cagr': f"{cfg.max_cagr_threshold:.1%}",
                'terminal_growth': f"{cfg.default_terminal_growth:.1%}",
                'max_terminal_value_ratio': f"{cfg.max_terminal_value_ratio:.0%}",
                'sector': sector,
                'industry': industry,
                'quality_adjustment': quality_grade,
                'valuation_discount': f"{valuation_discount:.1%}" if valuation_discount > 0 else None
            },
            'config_deltas': overrides
        }

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

    def is_applicable(self, company_type: str) -> bool:
        """Check if DCF applies to company type - excludes financial companies"""
        applicable_types = [
            CompanyType.MATURE_PROFITABLE.value,
            CompanyType.GROWTH_PROFITABLE.value,
            CompanyType.TURNAROUND.value,
            CompanyType.CYCLICAL.value,
            CompanyType.COMMODITY.value,
            CompanyType.REIT.value
        ]
        # Exclude financial companies as they have different business models
        excluded_types = [CompanyType.FINANCIAL.value, CompanyType.ETF.value]
        return company_type in applicable_types and company_type not in excluded_types
