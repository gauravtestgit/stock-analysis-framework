from typing import Dict, Any
import pandas as pd
import numpy as np
from ...interfaces.analyzer import IAnalyzer
from ...models.company import CompanyType
import pandas_ta as pd_ta

class TechnicalAnalyzer(IAnalyzer):
    """Technical analysis implementation"""
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform technical analysis"""
        try:
            price_data = data.get('price_data', {})
            hist = price_data.get('price_history')
            
            if hist is None or hist.empty:
                return {'error': 'No price history available'}
            
            current_price = hist['Close'].iloc[-1]
            # Calculate moving averages
            ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else None
            ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else None
            ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1] if len(hist) >= 200 else None
            
            # Calculate volatility
            volatility = hist['Close'].pct_change().std() * np.sqrt(252)
            
            # Support and resistance levels
            high_52w = hist['High'].max()
            low_52w = hist['Low'].min()
            
            # Volume analysis
            avg_volume = hist['Volume'].mean()
            recent_volume = hist['Volume'].iloc[-10:].mean()
            
            # Determine trend based on Moving averages
            price_targets = {}
            predicted_price = current_price
            ma_trend = ''
            
            if ma_200 is not None and ma_50 is not None:
                # Full trend analysis with all 3 MAs
                if current_price > ma_50 > ma_200:
                    ma_trend = 'Strong Uptrend'
                    price_targets['short_term'] = current_price * (1 + volatility * 0.5)  # 6-month target
                    predicted_price = price_targets['medium_term'] = current_price * (1 + volatility)  # 12-month target
                elif current_price < ma_50 < ma_200:
                    ma_trend = 'Strong Downtrend'
                    price_targets['short_term'] = current_price * (1 - volatility * 0.3)
                    predicted_price = price_targets['medium_term'] = max(ma_200, current_price * (1 - volatility * 0.5))
                elif current_price > ma_50:
                    ma_trend = 'Uptrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 + volatility * 0.5)  # 6-month target
                    price_targets['medium_term'] = current_price * (1 + volatility)  # 12-month target
                elif current_price < ma_50:
                    ma_trend = 'Downtrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 - volatility * 0.3)
                    price_targets['medium_term'] = max(ma_50, current_price * (1 - volatility * 0.5))
                else:
                    ma_trend = 'Sideways'
            elif ma_50 is not None:
                # Simple trend analysis with just 50-day MA
                if current_price > ma_50:
                    ma_trend = 'Short-term Uptrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 + volatility * 0.5)  # 6-month target
                    price_targets['medium_term'] = current_price * (1 + volatility)  # 12-month target
                elif current_price < ma_50:
                    ma_trend = 'Short-term Downtrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 - volatility * 0.3)
                    price_targets['medium_term'] = max(ma_50, current_price * (1 - volatility * 0.5))
                else:
                    ma_trend = 'Sideways'
            elif ma_20 is not None:
                if current_price > ma_20:
                    ma_trend = 'Near-term Uptrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 + volatility * 0.5)  # 6-month target
                    price_targets['medium_term'] = current_price * (1 + volatility)  # 12-month target
                elif current_price < ma_20:
                    ma_trend = 'Near-term Downtrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 - volatility * 0.3)
                    price_targets['medium_term'] = max(ma_20, current_price * (1 - volatility * 0.5))
                else:
                    ma_trend = 'Sideways'
            else:
                ma_trend = 'Insufficient Moving Averages Data'

            if current_price < high_52w * 0.8:  # More than 20% below high
                    price_targets['breakout_target'] = high_52w * 1.05  # 5% above resistance
            if current_price > low_52w * 1.2:  # More than 20% above low
                    price_targets['support_level'] = low_52w * 0.95  # 5% below support

            
            #Calculate RSI
            df = hist.copy()
            df['rsi'] = pd_ta.rsi(df['Close'],length=14)
            rsi_14 = df['rsi'].iloc[-1] if not df['rsi'].isna().iloc[-1] else None

            # Calculate range position and recommendation
            range_pos = ((current_price - low_52w) / (high_52w - low_52w)) * 100 if high_52w != low_52w else 50
            recommendation = self._get_technical_recommendation(range_pos, ma_trend)
                
            return {
                'method': 'Technical Analysis',
                'current_price': current_price,
                'predicted_price' : predicted_price,
                'price_targets' : price_targets,
                'recommendation': recommendation,
                'ma_20': ma_20,
                'ma_50': ma_50,
                'ma_200': ma_200,
                'trend': ma_trend,
                'volatility_annual': volatility,
                'high_52w': high_52w,
                'low_52w': low_52w,
                'distance_from_high': (current_price - high_52w) / high_52w,
                'distance_from_low': (current_price - low_52w) / low_52w,
                'volume_trend': f"Average Daily Volume:{avg_volume}, Trend: " + ('Above Average' if recent_volume > avg_volume * 1.2 else 'Below Average' if recent_volume < avg_volume * 0.8 else 'Normal'),
                'rsi_14' : rsi_14
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_technical_recommendation(self, range_pos: float, trend: str) -> str:
        """Generate technical recommendation based on actual ma_trend values"""
        # Strong bullish trends
        if trend == "Strong Uptrend" and range_pos > 70:
            return "Strong Buy"
        elif trend == "Strong Uptrend" and range_pos > 40:
            return "Buy"
        
        # Regular uptrends
        elif trend in ["Uptrend", "Short-term Uptrend", "Near-term Uptrend"] and range_pos > 60:
            return "Buy"
        elif trend in ["Uptrend", "Short-term Uptrend", "Near-term Uptrend"] and range_pos > 30:
            return "Hold"
        
        # Strong bearish trends
        elif trend == "Strong Downtrend" and range_pos < 30:
            return "Strong Sell"
        elif trend == "Strong Downtrend" and range_pos < 60:
            return "Sell"
        
        # Regular downtrends
        elif trend in ["Downtrend", "Short-term Downtrend", "Near-term Downtrend"] and range_pos < 40:
            return "Sell"
        elif trend in ["Downtrend", "Short-term Downtrend", "Near-term Downtrend"] and range_pos < 70:
            return "Hold"
        
        # Sideways or insufficient data
        elif trend in ["Sideways", "Insufficient Moving Averages Data"]:
            if range_pos > 80:
                return "Sell"  # Near resistance
            elif range_pos < 20:
                return "Buy"   # Near support
            else:
                return "Hold"
        
        # Default case
        else:
            return "Hold"
    
    def is_applicable(self, company_type: str) -> bool:
        """Technical analysis applies to all company types"""
        return True