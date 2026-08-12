import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from ....utils.cagr_calculations import get_cagr
from ....utils.debug_printer import debug_print
from ....config.config import FinanceConfig

class GrowthCalculator:
    """Handles growth rate calculations with sector-specific adjustments"""
    
    def __init__(self, config: FinanceConfig = None):
        self.config = config or FinanceConfig()
        self.cyclical_sectors = ["Semiconductors", "Auto Manufacturers", "Steel", "Mining", "Oil & Gas"]
        self.cyclical_industries = ["Semiconductors", "Auto Manufacturers", "Steel", "Aluminum", "Copper"]
    
    def calculate_fcf_cagr(self, ticker) -> float:
        """Calculate FCF CAGR using config parameters. When
        config.use_forward_guidance_growth is set, prefers the analyst
        next-year revenue consensus growth (used as a proxy - yfinance has no
        direct forward FCF estimate) over historical CAGR, falling back to
        historical CAGR when analyst coverage is thin or unavailable."""
        if self.config.use_forward_guidance_growth:
            forward_growth = self._get_forward_guidance_growth(ticker, 'revenue_estimate')
            if forward_growth is not None:
                debug_print(f"Using forward guidance revenue growth as FCF growth proxy: {forward_growth:.1%}")
                return forward_growth
            debug_print("Forward guidance unavailable for FCF - falling back to historical CAGR")
        try:
            return self._get_raw_fcf_cagr(ticker)
        except Exception as e:
            debug_print(f"FCF CAGR calculation error: {e}")
            return self.config.default_cagr

    def calculate_ebitda_cagr(self, ticker) -> float:
        """Calculate EBITDA CAGR using config parameters. When
        config.use_forward_guidance_growth is set, prefers the analyst
        next-year EPS consensus growth (used as a proxy - yfinance has no
        direct forward EBITDA estimate) over historical CAGR, falling back to
        historical CAGR when analyst coverage is thin or unavailable."""
        if self.config.use_forward_guidance_growth:
            forward_growth = self._get_forward_guidance_growth(ticker, 'earnings_estimate')
            if forward_growth is not None:
                debug_print(f"Using forward guidance EPS growth as EBITDA growth proxy: {forward_growth:.1%}")
                return forward_growth
            debug_print("Forward guidance unavailable for EBITDA - falling back to historical CAGR")
        try:
            return self._get_raw_ebitda_cagr(ticker)
        except Exception as e:
            debug_print(f"EBITDA CAGR calculation error: {e}")
            return self.config.default_cagr

    def _get_forward_guidance_growth(self, ticker, estimate_attr: str, min_analysts: int = 2) -> Optional[float]:
        """Pull the analyst consensus next-year ('+1y') growth rate from a
        yfinance forward-estimate DataFrame (earnings_estimate or
        revenue_estimate). Returns None on missing data or thin analyst
        coverage so callers fall back to historical CAGR."""
        try:
            df = getattr(ticker, estimate_attr)
            if df is None or df.empty or '+1y' not in df.index:
                return None
            row = df.loc['+1y']
            growth = row.get('growth')
            num_analysts = row.get('numberOfAnalysts')
            if growth is None or pd.isna(growth):
                return None
            if num_analysts is None or pd.isna(num_analysts) or num_analysts < min_analysts:
                debug_print(f"Forward guidance from {estimate_attr} has thin coverage "
                            f"({num_analysts} analysts) - skipping")
                return None
            # Loose sanity bound rather than the sector cap - analyst consensus is
            # already a real-world number, this just guards against a data glitch
            return max(min(float(growth), 1.5), -0.5)
        except Exception as e:
            debug_print(f"Forward guidance growth lookup failed for {estimate_attr}: {e}")
            return None

    def get_forward_guidance_summary(self, ticker) -> Dict:
        """Raw analyst forward-estimate details for display purposes,
        independent of which growth rate ultimately gets used for the DCF
        (which may fall back to historical CAGR if this is thin/unavailable).
        Missing fields are simply omitted rather than raising."""
        summary = {}

        try:
            eps_df = ticker.earnings_estimate
            if eps_df is not None and not eps_df.empty and '+1y' in eps_df.index:
                row = eps_df.loc['+1y']
                if pd.notna(row.get('growth')):
                    summary['eps_growth_next_year'] = float(row['growth'])
                if pd.notna(row.get('avg')):
                    summary['eps_estimate_next_year'] = float(row['avg'])
                if pd.notna(row.get('numberOfAnalysts')):
                    summary['eps_analysts_count'] = int(row['numberOfAnalysts'])
        except Exception as e:
            debug_print(f"Forward EPS guidance summary failed: {e}")

        try:
            rev_df = ticker.revenue_estimate
            if rev_df is not None and not rev_df.empty and '+1y' in rev_df.index:
                row = rev_df.loc['+1y']
                if pd.notna(row.get('growth')):
                    summary['revenue_growth_next_year'] = float(row['growth'])
                if pd.notna(row.get('avg')):
                    summary['revenue_estimate_next_year'] = float(row['avg'])
                if pd.notna(row.get('numberOfAnalysts')):
                    summary['revenue_analysts_count'] = int(row['numberOfAnalysts'])
        except Exception as e:
            debug_print(f"Forward revenue guidance summary failed: {e}")

        try:
            growth_df = ticker.growth_estimates
            if growth_df is not None and not growth_df.empty and 'LTG' in growth_df.index:
                ltg = growth_df.loc['LTG'].get('stockTrend')
                if pd.notna(ltg):
                    summary['long_term_growth_estimate'] = float(ltg)
        except Exception as e:
            debug_print(f"Long-term growth estimate lookup failed: {e}")

        return summary
    
    def _get_raw_fcf_cagr(self, ticker) -> float:
        """Extract raw FCF CAGR from existing logic"""
        from ....utils import cash_flow_data_handler as cf_handler
        
        cashflow = ticker.cashflow
        if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
            fcf_data = cashflow.loc['Free Cash Flow'].dropna()
        else:
            estimated_fcf = cf_handler.CashFlowDataHandler(ticker.info.get('symbol')).estimate_fcf_from_net_income()
            fcf_data = estimated_fcf.dropna() if estimated_fcf is not None else pd.Series()
        
        if fcf_data is None or fcf_data.empty or len(fcf_data) < 2:
            raise Exception("No Cash Flow Data Available")
        
        fcf_values = fcf_data.values
        debug_print(f'FCF Beginning: ${fcf_values[-1]:,.2f}, FCF Ending: ${fcf_values[0]:,.2f}, Period: {len(fcf_values)}')
        
        return get_cagr(fcf_values, simple_cagr=False, 
                       max_threshold=self.config.max_cagr_threshold,
                       default=self.config.default_cagr)
    
    def _get_raw_ebitda_cagr(self, ticker) -> float:
        """Extract raw EBITDA CAGR from existing logic"""
        ebitda_data = ticker.income_stmt.loc['EBITDA'].dropna()
        ebitda_values = ebitda_data.values
        debug_print(f'Ebitda Beginning: ${ebitda_values[-1]:,.2f}, Ebitda Ending: ${ebitda_values[0]:,.2f}, Period: {len(ebitda_values)}')
        
        return get_cagr(ebitda_values,
                       max_threshold=self.config.max_cagr_threshold,
                       default=self.config.default_cagr,
                       simple_cagr=False)
    
    def _is_cyclical(self, sector: str, industry: str) -> bool:
        """Check if company is in cyclical sector/industry"""
        return (sector in self.cyclical_sectors or 
                industry in self.cyclical_industries)
    
    def _handle_cyclical_growth(self, ticker, raw_cagr: float, metric_type: str = "fcf") -> float:
        """Handle growth for cyclical companies"""
        debug_print(f"Applying cyclical adjustments for {metric_type.upper()}")
        
        # For severely declining cyclical companies (like MU with -63% FCF decline)
        if raw_cagr < -0.30:  # >30% decline
            debug_print(f"Severe decline detected ({raw_cagr:.1%}), using conservative negative growth")
            return max(raw_cagr * 0.2, -0.10)  # 20% of decline or -10% max negative
        
        # For moderately declining cyclical companies  
        elif raw_cagr < 0:
            debug_print(f"Negative growth detected ({raw_cagr:.1%}), using modest recovery")
            return max(raw_cagr * 0.5, -0.02)  # Half the decline or -2% max negative
        
        # For positive growth, cap at reasonable levels for cyclicals
        else:
            return min(raw_cagr, 0.08)  # Cap cyclical growth at 8%
    
    def _apply_growth_constraints(self, raw_cagr: float) -> float:
        """Apply general growth constraints"""
        # Cap extreme positive growth
        if raw_cagr > self.config.max_cagr_threshold:
            debug_print(f"Capping growth from {raw_cagr:.1%} to {self.config.max_cagr_threshold:.1%}")
            return self.config.max_cagr_threshold
        
        # Handle negative growth
        if raw_cagr < -0.20:  # >20% decline
            debug_print(f"Large decline detected ({raw_cagr:.1%}), using conservative projection")
            return max(raw_cagr * 0.5, 0.03)  # Half the decline or 3% min
        
        return raw_cagr