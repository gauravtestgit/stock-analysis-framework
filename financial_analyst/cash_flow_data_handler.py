import yfinance as yf
import pandas as pd
import numpy as np
from util.debug_printer import debug_print
import os
import warnings
warnings.filterwarnings('ignore')

class CashFlowDataHandler:
    """
    Handle missing or incomplete cash flow data for DCF analysis
    """
    
    def __init__(self, ticker_symbol):
        self.ticker_symbol = ticker_symbol.upper()
        self.ticker = yf.Ticker(ticker_symbol)
        self.data_quality = {}
        
    def analyze_data_availability(self):
        """
        Analyze what financial data is available for the company
        """
        debug_print(f"\n{'='*60}")
        debug_print(f"DATA AVAILABILITY ANALYSIS - {self.ticker_symbol}")
        debug_print(f"{'='*60}")
        
        availability = {
            'cash_flow': False,
            'income_statement': False,
            'balance_sheet': False,
            'company_info': False,
            'price_data': False
        }
        
        try:
            # Check cash flow data
            cashflow = self.ticker.cashflow
            if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
                fcf_data = cashflow.loc['Free Cash Flow'].dropna()
                if len(fcf_data) > 0:
                    availability['cash_flow'] = True
                    debug_print(f"✓ Cash Flow: {len(fcf_data)} years of FCF data")
                else:
                    debug_print(f"✗ Cash Flow: FCF row exists but all NaN values")
            else:
                debug_print(f"✗ Cash Flow: No FCF data available")
                
        except Exception as e:
            debug_print(f"✗ Cash Flow: Error accessing data - {str(e)[:50]}...")
        
        try:
            # Check income statement
            income_stmt = self.ticker.income_stmt
            if not income_stmt.empty:
                availability['income_statement'] = True
                revenue_data = income_stmt.loc['Total Revenue'].dropna() if 'Total Revenue' in income_stmt.index else pd.Series([])
                net_income_data = income_stmt.loc['Net Income'].dropna() if 'Net Income' in income_stmt.index else pd.Series([])
                ebitda_data = income_stmt.loc['EBITDA'].dropna() if 'EBITDA' in income_stmt.index else pd.Series([])
                
                debug_print(f"✓ Income Statement: {len(revenue_data)} years revenue, {len(net_income_data)} years net income, {len(ebitda_data)} years EBITDA")
            else:
                debug_print(f"✗ Income Statement: No data available")
        except Exception as e:
            debug_print(f"✗ Income Statement: Error - {str(e)[:50]}...")
            
        try:
            # Check balance sheet
            balance_sheet = self.ticker.balance_sheet
            if not balance_sheet.empty:
                availability['balance_sheet'] = True
                debug_print(f"✓ Balance Sheet: {len(balance_sheet.columns)} years available")
            else:
                debug_print(f"✗ Balance Sheet: No data available")
        except Exception as e:
            debug_print(f"✗ Balance Sheet: Error - {str(e)[:50]}...")
            
        try:
            # Check company info
            info = self.ticker.info
            if info and len(info) > 10:  # Basic check for meaningful data
                availability['company_info'] = True
                market_cap = info.get('marketCap', 0)
                sector = info.get('sector', 'Unknown')
                debug_print(f"✓ Company Info: Market cap ${market_cap/1e9:.1f}B, Sector: {sector}")
            else:
                debug_print(f"✗ Company Info: Limited data available")
        except Exception as e:
            debug_print(f"✗ Company Info: Error - {str(e)[:50]}...")
            
        try:
            # Check price data
            hist = self.ticker.history(period="1y")
            if not hist.empty:
                availability['price_data'] = True
                debug_print(f"✓ Price Data: {len(hist)} days available")
            else:
                debug_print(f"✗ Price Data: No historical prices")
        except Exception as e:
            debug_print(f"✗ Price Data: Error - {str(e)[:50]}...")
        
        self.data_quality = availability
        return availability
    
    def should_skip_dcf_analysis(self):
        """
        Determine if DCF analysis should be skipped entirely
        """
        reasons_to_skip = []
        
        # Must have basic company info
        if not self.data_quality.get('company_info', False):
            reasons_to_skip.append("No basic company information available")
        
        # Must have either cash flow OR income statement data
        if not self.data_quality.get('cash_flow', False) and not self.data_quality.get('income_statement', False):
            reasons_to_skip.append("No financial statements available")
        
        # Check if it's likely a dead/delisted company
        try:
            info = self.ticker.info
            if info.get('marketCap', 0) == 0 and not self.data_quality.get('price_data', False):
                reasons_to_skip.append("Appears to be delisted or inactive")
        except:
            pass
        
        return reasons_to_skip
    
    def get_alternative_dcf_approaches(self):
        """
        Suggest alternative DCF approaches when cash flow data is missing
        """
        approaches = []
        
        # Check what data we have
        has_cashflow = self.data_quality.get('cash_flow', False)
        has_income = self.data_quality.get('income_statement', False)
        has_balance = self.data_quality.get('balance_sheet', False)
        
        if not has_cashflow:
            debug_print(f"\n⚠️  No Free Cash Flow data available for {self.ticker_symbol}")
            debug_print("Alternative approaches:")
            
            if has_income:
                approaches.append({
                    'method': 'EBITDA-based DCF',
                    'description': 'Use EBITDA multiples instead of FCF',
                    'feasible': True,
                    'reliability': 'Medium'
                })
                
                approaches.append({
                    'method': 'Net Income + D&A Proxy',
                    'description': 'Estimate FCF from Net Income + Depreciation',
                    'feasible': True,
                    'reliability': 'Low-Medium'
                })
                
                approaches.append({
                    'method': 'Revenue Multiple Valuation',
                    'description': 'Use revenue multiples (P/S ratios)',
                    'feasible': True,
                    'reliability': 'Low'
                })
            
            if has_balance:
                approaches.append({
                    'method': 'Asset-based Valuation',
                    'description': 'Book value and asset liquidation approach',
                    'feasible': True,
                    'reliability': 'Medium (for asset-heavy companies)'
                })
            
            approaches.append({
                'method': 'Comparable Company Analysis',
                'description': 'Use industry multiples (P/E, EV/EBITDA, etc.)',
                'feasible': True,
                'reliability': 'Medium-High'
            })
            
            approaches.append({
                'method': 'Skip DCF Analysis',
                'description': 'Focus on other valuation methods',
                'feasible': True,
                'reliability': 'N/A'
            })
        
        return approaches
    
    def estimate_fcf_from_net_income(self):
        """
        Rough estimation of FCF when cash flow statement is not available
        """
        try:
            income_stmt = self.ticker.income_stmt
            balance_sheet = self.ticker.balance_sheet
            
            if income_stmt.empty:
                debug_print("Cannot estimate FCF - no income statement data")
                return None
            
            # Get net income
            if 'Net Income' not in income_stmt.index:
                debug_print("Cannot estimate FCF - no net income data")
                return None
                
            net_incomes = income_stmt.loc['Net Income']
            
            debug_print(f"\nEstimating FCF from Net Income for {self.ticker_symbol}:")
            debug_print(f"Available Net Income data: {len(net_incomes)} years")
            
            estimated_fcf = {}
            
            for date, net_income in net_incomes.items():
                if pd.isna(net_income):
                    continue
                    
                # Start with net income
                fcf_estimate = net_income
                
                # Add back depreciation & amortization (if available)
                try:
                    if not income_stmt.empty:
                        # Look for D&A in various possible locations
                        da_keys = ['Depreciation And Amortization', 'Depreciation', 'Amortization']
                        da_amount = 0
                        
                        for key in da_keys:
                            if key in income_stmt.index:
                                da_value = income_stmt.loc[key, date]
                                if not pd.isna(da_value):
                                    da_amount += abs(da_value)  # Make positive
                                    break
                        
                        fcf_estimate += da_amount
                        
                except Exception as e:
                    debug_print(f"  Warning: Could not add D&A for {date}: {e}")
                
                # Subtract estimated capex (rough estimate as % of revenue)
                try:
                    if 'Total Revenue' in income_stmt.index:
                        revenue = income_stmt.loc['Total Revenue', date]
                        if not pd.isna(revenue):
                            # Rough estimate: capex = 3-5% of revenue for most companies
                            estimated_capex = revenue * 0.04  # 4% estimate
                            fcf_estimate -= estimated_capex
                            
                except Exception as e:
                    debug_print(f"  Warning: Could not estimate capex for {date}: {e}")
                
                estimated_fcf[date] = fcf_estimate
                
            if estimated_fcf:
                debug_print("Estimated FCF by year:")
                for date, fcf in estimated_fcf.items():
                    debug_print(f"  {date.year}: ${fcf:,.0f}")
                    
                return pd.Series(estimated_fcf)
            else:
                debug_print("Could not estimate any FCF values")
                return None
                
        except Exception as e:
            debug_print(f"FCF estimation failed: {e}")
            return None
    
    def run_ebitda_based_dcf(self, terminal_growth=0.025, discount_rate=0.10, years=5):
        """
        Alternative DCF using EBITDA multiples when FCF is not available
        """
        try:
            income_stmt = self.ticker.income_stmt
            
            if 'EBITDA' not in income_stmt.index:
                debug_print("Cannot run EBITDA-based DCF - no EBITDA data")
                return None
            
            ebitda_data = income_stmt.loc['EBITDA'].dropna()
            
            if len(ebitda_data) < 2:
                debug_print("Insufficient EBITDA data for growth calculation")
                return None
            
            debug_print(f"\n{'='*50}")
            debug_print(f"EBITDA-BASED DCF FOR {self.ticker_symbol}")
            debug_print(f"{'='*50}")
            
            # Calculate EBITDA growth
            current_ebitda = ebitda_data.iloc[0]
            past_ebitda = ebitda_data.iloc[-1]
            periods = len(ebitda_data) - 1
            
            if past_ebitda <= 0 or current_ebitda <= 0:
                debug_print("Negative EBITDA values - cannot calculate growth")
                return None
            
            ebitda_cagr = (current_ebitda / past_ebitda) ** (1/periods) - 1
            ebitda_cagr = min(ebitda_cagr, 0.15)  # Cap at 15%
            
            debug_print(f"Current EBITDA: ${current_ebitda:,.0f}")
            debug_print(f"EBITDA CAGR: {ebitda_cagr:.2%}")
            
            # Project EBITDA
            projected_ebitdas = []
            for year in range(1, years + 1):
                future_ebitda = current_ebitda * ((1 + ebitda_cagr) ** year)
                projected_ebitdas.append(future_ebitda)
                debug_print(f"Year {year} EBITDA: ${future_ebitda:,.0f}")
            
            # Terminal EBITDA
            terminal_ebitda = projected_ebitdas[-1] * (1 + terminal_growth)
            
            # Get industry EV/EBITDA multiple
            try:
                current_ev_ebitda = self.ticker.info.get('enterpriseToEbitda', 12)
                if current_ev_ebitda is None or current_ev_ebitda <= 0:
                    current_ev_ebitda = 12  # Default multiple
            except:
                current_ev_ebitda = 12
            
            # Terminal value
            terminal_enterprise_value = terminal_ebitda * current_ev_ebitda
            terminal_pv = terminal_enterprise_value / ((1 + discount_rate) ** years)
            
            debug_print(f"Terminal EBITDA: ${terminal_ebitda:,.0f}")
            debug_print(f"EV/EBITDA Multiple: {current_ev_ebitda:.1f}x")
            debug_print(f"Terminal Enterprise Value: ${terminal_enterprise_value:,.0f}")
            debug_print(f"Terminal PV: ${terminal_pv:,.0f}")
            
            # This is a simplified version - you would need to complete the valuation
            debug_print(f"\n⚠️  This is a simplified EBITDA-based approach")
            debug_print(f"Complete DCF would require:")
            debug_print(f"• Working capital adjustments")
            debug_print(f"• Capital expenditure estimates") 
            debug_print(f"• Tax considerations")
            debug_print(f"• Debt adjustments")
            
            return {
                'method': 'EBITDA-based DCF',
                'current_ebitda': current_ebitda,
                'ebitda_cagr': ebitda_cagr,
                'terminal_value': terminal_pv,
                'status': 'incomplete_example'
            }
            
        except Exception as e:
            debug_print(f"EBITDA-based DCF failed: {e}")
            return None
    
    def comprehensive_analysis_recommendation(self):
        """
        Provide comprehensive recommendation on how to handle the company
        """
        debug_print(f"\n{'='*70}")
        debug_print(f"DCF ANALYSIS RECOMMENDATION - {self.ticker_symbol}")
        debug_print(f"{'='*70}")
        
        # Analyze data availability
        self.analyze_data_availability()
        
        # Check if analysis should be skipped
        skip_reasons = self.should_skip_dcf_analysis()
        
        if skip_reasons:
            debug_print(f"\n🚫 RECOMMENDATION: SKIP DCF ANALYSIS")
            debug_print(f"Reasons:")
            for reason in skip_reasons:
                debug_print(f"  • {reason}")
            debug_print(f"\nSuggested alternatives:")
            debug_print(f"  • Use screening tools to find better candidates")
            debug_print(f"  • Focus on companies with complete financial data")
            debug_print(f"  • Consider ETFs for sector/industry exposure")
            return "SKIP"
        
        # If we have some data, suggest approaches
        if not self.data_quality.get('cash_flow', False):
            debug_print(f"\n⚠️  LIMITED DCF FEASIBILITY")
            alternatives = self.get_alternative_dcf_approaches()
            
            debug_print(f"\nRecommended approach priority:")
            for i, approach in enumerate(alternatives, 1):
                reliability = approach['reliability']
                debug_print(f"{i}. {approach['method']} - Reliability: {reliability}")
                debug_print(f"   {approach['description']}")
            
            # Try the estimation approach
            if self.data_quality.get('income_statement', False):
                debug_print(f"\n📊 Attempting FCF estimation from available data...")
                estimated_fcf = self.estimate_fcf_from_net_income()
                
                if estimated_fcf is not None:
                    debug_print(f"✓ FCF estimation successful - can proceed with modified DCF")
                    return "PROCEED_WITH_ESTIMATION"
                else:
                    debug_print(f"✗ FCF estimation failed")
                    
                # Try EBITDA approach
                debug_print(f"\n📊 Attempting EBITDA-based valuation...")
                ebitda_result = self.run_ebitda_based_dcf()
                
                if ebitda_result:
                    debug_print(f"✓ EBITDA-based approach feasible")
                    return "PROCEED_WITH_EBITDA"
        else:
            debug_print(f"\n✅ RECOMMENDATION: PROCEED WITH STANDARD DCF")
            debug_print(f"All necessary data appears to be available")
            return "PROCEED_STANDARD"
        
        debug_print(f"\n🤷 RECOMMENDATION: INSUFFICIENT DATA FOR RELIABLE DCF")
        debug_print(f"Consider using relative valuation methods instead")
        return "INSUFFICIENT_DATA"

def test_missing_cashflow_scenarios():
    """
    Test the framework with various scenarios
    """
    os.environ['DEBUG'] = 'true'
    test_cases = [
        'AAPL',    # Should have complete data
        'TSLA',    # Should have complete data
        'AACB',     # May have issues due to COVID
        'BRK-A',   # Berkshire - unique structure
        'INVALID'  # Invalid ticker
    ]
    
    debug_print("="*100)
    debug_print("TESTING MISSING CASH FLOW HANDLING")
    debug_print("="*100)
    
    for ticker in test_cases:
        debug_print(f"\n{'='*80}")
        debug_print(f"TESTING: {ticker}")
        debug_print(f"{'='*80}")
        
        try:
            handler = CashFlowDataHandler(ticker)
            recommendation = handler.comprehensive_analysis_recommendation()
            debug_print(f"\nFinal recommendation: {recommendation}")
            
        except Exception as e:
            debug_print(f"Error testing {ticker}: {e}")

if __name__ == "__main__":
    test_missing_cashflow_scenarios()