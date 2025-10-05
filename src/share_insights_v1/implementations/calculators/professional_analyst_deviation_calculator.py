import yfinance as yf
import requests
import pandas as pd
import numpy as np
from typing import Dict, Optional

class ProfessionalAnalystData:
    def __init__(self):
        self.cache = {}
    
    def get_analyst_data(self, ticker: str) -> Dict:
        """Fetch analyst data from multiple sources"""
        if ticker in self.cache:
            return self.cache[ticker]
        
        data = {}
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Price targets
            data['target_price'] = info.get('targetMeanPrice')
            data['target_high'] = info.get('targetHighPrice')
            data['target_low'] = info.get('targetLowPrice')
            
            # Recommendations
            data['recommendation'] = info.get('recommendationMean')
            data['recommendation_key'] = info.get('recommendationKey')
            
            # Estimates
            data['forward_eps'] = info.get('forwardEps')
            data['eps_current_year'] = info.get('trailingEps')
            
            # Growth estimates
            data['earnings_growth'] = info.get('earningsGrowth')
            data['revenue_growth'] = info.get('revenueGrowth')
            
            # Analyst count
            data['analyst_count'] = info.get('numberOfAnalystOpinions', 0)
            
            self.cache[ticker] = data
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            data = {}
        
        return data

def calculate_consensus_deviation(our_price: float, analyst_target: float, 
                                current_price: float) -> Dict:
    """Calculate deviation scores between our analysis and analyst consensus"""
    
    if not all([our_price, analyst_target, current_price]):
        return {'deviation_score': None, 'confidence': 'Low'}
    
    # Calculate percentage differences
    our_upside = (our_price - current_price) / current_price
    analyst_upside = (analyst_target - current_price) / current_price
    
    # Investment-focused alignment: both showing >20% upside is convergence
    investment_threshold = 0.20  # 20% upside threshold
    
    # Check for directional convergence
    both_bullish = our_upside > investment_threshold and analyst_upside > investment_threshold
    both_bearish = our_upside < -investment_threshold and analyst_upside < -investment_threshold
    
    # Deviation score (0-100, lower = more aligned)
    deviation = abs(our_upside - analyst_upside) * 100
    
    # Investment-focused confidence scoring
    if both_bullish or both_bearish:
        confidence = 'High'  # Both see significant opportunity/risk
        alignment = 'Investment_Aligned'
    elif deviation < 20:
        confidence = 'High'
        alignment = 'Precise_Aligned'
    elif deviation < 50:
        confidence = 'Medium'
        alignment = 'Moderate_Aligned'
    else:
        confidence = 'Low'
        alignment = 'Divergent'
    
    return {
        'deviation_score': round(deviation, 1),
        'our_upside': round(our_upside * 100, 1),
        'analyst_upside': round(analyst_upside * 100, 1),
        'confidence': confidence,
        'alignment': alignment,
        'both_bullish': both_bullish,
        'both_bearish': both_bearish
    }

def validate_against_analysts(row: pd.Series, analyst_data: Dict) -> list:
    """Enhanced validation using analyst data"""
    validations = []
    
    current_price = pd.to_numeric(str(row['Current_Price']).replace('$', '').replace(',', ''), errors='coerce')
    dcf_price = pd.to_numeric(str(row['DCF_Price']).replace('$', '').replace(',', ''), errors='coerce')
    
    # Price target validation
    target_price = analyst_data.get('target_price')
    if target_price and dcf_price and current_price:
        deviation_data = calculate_consensus_deviation(dcf_price, target_price, current_price)
        
        if deviation_data['deviation_score'] and deviation_data['deviation_score'] > 50:
            validations.append(f"ANALYST_DIVERGENCE: {deviation_data['deviation_score']}% deviation from consensus")
        
        # Contrarian position detection
        our_direction = 1 if dcf_price > current_price else -1
        analyst_direction = 1 if target_price > current_price else -1
        
        if our_direction != analyst_direction:
            validations.append("CONTRARIAN_POSITION: Opposite direction vs analyst consensus")
    
    # Recommendation alignment
    our_rec = str(row.get('Recommendation', '')).upper()
    analyst_rec_mean = analyst_data.get('recommendation')
    
    if analyst_rec_mean:
        # Convert numeric recommendation to text (1=Strong Buy, 5=Strong Sell)
        rec_map = {1: 'BUY', 2: 'BUY', 3: 'HOLD', 4: 'SELL', 5: 'SELL'}
        analyst_rec = rec_map.get(round(analyst_rec_mean), 'HOLD')
        
        if 'BUY' in our_rec and analyst_rec == 'SELL':
            validations.append("REC_CONFLICT: Buy recommendation vs analyst sell consensus")
        elif 'SELL' in our_rec and analyst_rec == 'BUY':
            validations.append("REC_CONFLICT: Sell recommendation vs analyst buy consensus")
    
    return validations

class ProfessionalVsAlgorithmicComparison:
    def __init__(self):
        self.analyst_provider = ProfessionalAnalystData()
    
    def compare_analysis(self, stock_row: pd.Series) -> Dict:
        """Compare our algorithmic analysis with professional analyst consensus"""
        
        ticker = stock_row['Ticker']
        analyst_data = self.analyst_provider.get_analyst_data(ticker)
        
        # Extract our analysis
        current_price = pd.to_numeric(str(stock_row['Current_Price']).replace('$', '').replace(',', ''), errors='coerce')
        dcf_price = pd.to_numeric(str(stock_row['DCF_Price']).replace('$', '').replace(',', ''), errors='coerce')
        our_rec = str(stock_row.get('Recommendation', ''))
        
        # Professional data
        analyst_target = analyst_data.get('target_price')
        analyst_rec = analyst_data.get('recommendation_key', 'hold')
        analyst_count = analyst_data.get('analyst_count', 0)
        
        # Calculate comparison metrics
        comparison = {
            'ticker': ticker,
            'current_price': current_price,
            'our_dcf_price': dcf_price,
            'analyst_target': analyst_target,
            'our_recommendation': our_rec,
            'analyst_recommendation': analyst_rec,
            'analyst_count': analyst_count
        }
        
        # Deviation analysis
        if all([dcf_price, analyst_target, current_price]):
            deviation_data = calculate_consensus_deviation(dcf_price, analyst_target, current_price)
            comparison.update(deviation_data)
        
        # Validation flags
        comparison['validation_flags'] = validate_against_analysts(stock_row, analyst_data)
        
        # Investment-focused assessment
        alignment = comparison.get('alignment', 'Divergent')
        both_bullish = comparison.get('both_bullish', False)
        both_bearish = comparison.get('both_bearish', False)
        
        if alignment == 'Investment_Aligned' or alignment == 'Precise_Aligned':
            comparison['assessment'] = 'INVESTMENT_ALIGNED'
        elif both_bullish:
            comparison['assessment'] = 'BULLISH_CONVERGENCE'
        elif both_bearish:
            comparison['assessment'] = 'BEARISH_CONVERGENCE'
        elif 'CONTRARIAN_POSITION' in str(comparison['validation_flags']):
            comparison['assessment'] = 'CONTRARIAN_OPPORTUNITY'
        elif comparison.get('deviation_score', 0) > 100:
            comparison['assessment'] = 'HIGH_DIVERGENCE'
        else:
            comparison['assessment'] = 'MODERATE_DEVIATION'
        
        return comparison
    
    def batch_comparison(self, df_batch: pd.DataFrame) -> pd.DataFrame:
        """Run comparison analysis on a batch of stocks"""
        
        comparisons = []
        for idx, row in df_batch.iterrows():
            try:
                comparison = self.compare_analysis(row)
                comparisons.append(comparison)
            except Exception as e:
                print(f"Error comparing {row.get('Ticker', 'Unknown')}: {e}")
                continue
        
        return pd.DataFrame(comparisons)