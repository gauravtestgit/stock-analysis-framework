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
            
            # Calculate professional support/resistance levels
            support_resistance = self._calculate_support_resistance(hist, current_price)
            
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

            # Add support/resistance to price targets
            if support_resistance['resistance_levels']:
                price_targets['breakout_target'] = support_resistance['resistance_levels'][0]
            if support_resistance['support_levels']:
                price_targets['support_level'] = support_resistance['support_levels'][0]

            
            # Calculate technical indicators
            df = hist.copy()
            
            # RSI
            df['rsi'] = pd_ta.rsi(df['Close'], length=14)
            rsi_14 = df['rsi'].iloc[-1] if not df['rsi'].isna().iloc[-1] else None
            
            # MACD
            macd_data = pd_ta.macd(df['Close'])
            macd_line = macd_data['MACD_12_26_9'].iloc[-1] if 'MACD_12_26_9' in macd_data.columns else None
            macd_signal = macd_data['MACDs_12_26_9'].iloc[-1] if 'MACDs_12_26_9' in macd_data.columns else None
            macd_histogram = macd_data['MACDh_12_26_9'].iloc[-1] if 'MACDh_12_26_9' in macd_data.columns else None
            
            # Bollinger Bands - Manual calculation
            if len(df) >= 20:
                sma_20 = df['Close'].rolling(window=20).mean().iloc[-1]
                std_20 = df['Close'].rolling(window=20).std().iloc[-1]
                bb_upper = sma_20 + (std_20 * 2)
                bb_lower = sma_20 - (std_20 * 2)
                bb_middle = sma_20
            else:
                bb_upper = None
                bb_lower = None
                bb_middle = None
            
            # Stochastic
            stoch_data = pd_ta.stoch(df['High'], df['Low'], df['Close'])
            stoch_k = stoch_data['STOCHk_14_3_3'].iloc[-1] if 'STOCHk_14_3_3' in stoch_data.columns else None
            stoch_d = stoch_data['STOCHd_14_3_3'].iloc[-1] if 'STOCHd_14_3_3' in stoch_data.columns else None
            
            # ADX (Average Directional Index) - Trend Strength
            adx_data = pd_ta.adx(df['High'], df['Low'], df['Close'], length=14)
            adx = adx_data['ADX_14'].iloc[-1] if 'ADX_14' in adx_data.columns else None
            di_plus = adx_data['DMP_14'].iloc[-1] if 'DMP_14' in adx_data.columns else None
            di_minus = adx_data['DMN_14'].iloc[-1] if 'DMN_14' in adx_data.columns else None
            
            # ATR (Average True Range) - Volatility
            atr_data = pd_ta.atr(df['High'], df['Low'], df['Close'], length=14)
            atr = atr_data.iloc[-1] if not atr_data.isna().iloc[-1] else None
            atr_percent = (atr / current_price * 100) if atr else None
            
            # Calculate range position and enhanced recommendation
            range_pos = ((current_price - low_52w) / (high_52w - low_52w)) * 100 if high_52w != low_52w else 50
            
            # Enhanced technical signals
            technical_signals = self._analyze_technical_signals({
                'current_price': current_price,
                'ma_20': ma_20, 'ma_50': ma_50, 'ma_200': ma_200,
                'rsi': rsi_14,
                'macd_line': macd_line, 'macd_signal': macd_signal, 'macd_histogram': macd_histogram,
                'bb_upper': bb_upper, 'bb_lower': bb_lower, 'bb_middle': bb_middle,
                'stoch_k': stoch_k, 'stoch_d': stoch_d,
                'range_pos': range_pos,
                'ma_trend': ma_trend,
                'adx': adx, 'di_plus': di_plus, 'di_minus': di_minus,
                'atr': atr, 'atr_percent': atr_percent
            })
            
            recommendation = technical_signals['recommendation']
            
            # Adjust predicted price based on enhanced signals recommendation
            if recommendation in ['Strong Sell', 'Sell']:
                predicted_price = current_price * (1 - volatility * 0.3)  # Bearish target
            elif recommendation in ['Strong Buy', 'Buy']:
                predicted_price = current_price * (1 + volatility * 0.8)  # Bullish target
            # Keep existing predicted_price for Hold
                
            chart_data = price_data.get('chart_data', {})
            
            return {
                'method': 'Technical Analysis',
                'current_price': current_price,
                'predicted_price': predicted_price,
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
                'rsi_14': rsi_14,
                'macd_line': macd_line,
                'macd_signal': macd_signal,
                'macd_histogram': macd_histogram,
                'bb_upper': bb_upper,
                'bb_lower': bb_lower,
                'bb_middle': bb_middle,
                'stoch_k': stoch_k,
                'stoch_d': stoch_d,
                'adx': adx,
                'di_plus': di_plus,
                'di_minus': di_minus,
                'atr': atr,
                'atr_percent': atr_percent,
                'technical_signals': technical_signals,
                'support_resistance': support_resistance,
                'chart_data': chart_data
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_technical_signals(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced technical analysis with multiple indicators"""
        signals = {'bullish': 0, 'bearish': 0, 'signals': []}
        
        # Moving Average Signals
        if indicators['ma_trend'] == "Strong Uptrend":
            signals['bullish'] += 3
            signals['signals'].append("Strong MA uptrend")
        elif indicators['ma_trend'] in ["Uptrend", "Short-term Uptrend"]:
            signals['bullish'] += 2
            signals['signals'].append("MA uptrend")
        elif indicators['ma_trend'] == "Strong Downtrend":
            signals['bearish'] += 3
            signals['signals'].append("Strong MA downtrend")
        elif indicators['ma_trend'] in ["Downtrend", "Short-term Downtrend"]:
            signals['bearish'] += 2
            signals['signals'].append("MA downtrend")
        
        # RSI Signals
        if indicators['rsi'] is not None:
            if indicators['rsi'] < 30:
                signals['bullish'] += 2
                signals['signals'].append(f"RSI oversold ({indicators['rsi']:.1f})")
            elif indicators['rsi'] > 70:
                signals['bearish'] += 2
                signals['signals'].append(f"RSI overbought ({indicators['rsi']:.1f})")
            elif 30 <= indicators['rsi'] <= 50:
                signals['bullish'] += 1
                signals['signals'].append("RSI bullish zone")
            elif 50 <= indicators['rsi'] <= 70:
                signals['bearish'] += 1
                signals['signals'].append("RSI bearish zone")
        
        # MACD Signals
        if indicators['macd_line'] is not None and indicators['macd_signal'] is not None:
            if indicators['macd_line'] > indicators['macd_signal']:
                signals['bullish'] += 2
                signals['signals'].append("MACD bullish crossover")
            else:
                signals['bearish'] += 2
                signals['signals'].append("MACD bearish crossover")
            
            if indicators['macd_histogram'] is not None:
                if indicators['macd_histogram'] > 0:
                    signals['bullish'] += 1
                    signals['signals'].append("MACD histogram positive")
                else:
                    signals['bearish'] += 1
                    signals['signals'].append("MACD histogram negative")
        
        # Bollinger Bands Signals
        if all(x is not None for x in [indicators['bb_upper'], indicators['bb_lower'], indicators['current_price']]):
            if indicators['current_price'] <= indicators['bb_lower']:
                signals['bullish'] += 2
                signals['signals'].append("Price at lower Bollinger Band")
            elif indicators['current_price'] >= indicators['bb_upper']:
                signals['bearish'] += 2
                signals['signals'].append("Price at upper Bollinger Band")
        
        # Stochastic Signals
        if indicators['stoch_k'] is not None and indicators['stoch_d'] is not None:
            if indicators['stoch_k'] < 20 and indicators['stoch_d'] < 20:
                signals['bullish'] += 1
                signals['signals'].append("Stochastic oversold")
            elif indicators['stoch_k'] > 80 and indicators['stoch_d'] > 80:
                signals['bearish'] += 1
                signals['signals'].append("Stochastic overbought")
        
        # Range Position Signals
        if indicators['range_pos'] < 20:
            signals['bullish'] += 1
            signals['signals'].append("Near 52-week low")
        elif indicators['range_pos'] > 80:
            signals['bearish'] += 1
            signals['signals'].append("Near 52-week high")
        
        # ADX Signals (Trend Strength)
        if indicators.get('adx') is not None:
            adx = indicators['adx']
            di_plus = indicators.get('di_plus')
            di_minus = indicators.get('di_minus')
            
            if adx > 25:  # Strong trend
                if di_plus and di_minus and di_plus > di_minus:
                    signals['bullish'] += 2
                    signals['signals'].append(f"Strong uptrend (ADX {adx:.1f})")
                elif di_plus and di_minus and di_minus > di_plus:
                    signals['bearish'] += 2
                    signals['signals'].append(f"Strong downtrend (ADX {adx:.1f})")
            elif adx < 20:  # Weak trend / ranging
                signals['signals'].append(f"Weak trend/ranging (ADX {adx:.1f})")
        
        # ATR Signals (Volatility context)
        if indicators.get('atr_percent') is not None:
            atr_pct = indicators['atr_percent']
            if atr_pct > 5:  # High volatility
                signals['signals'].append(f"High volatility (ATR {atr_pct:.1f}%)")
            elif atr_pct < 2:  # Low volatility
                signals['signals'].append(f"Low volatility (ATR {atr_pct:.1f}%)")
        
        # Generate recommendation based on signal strength
        net_signal = signals['bullish'] - signals['bearish']
        
        if net_signal >= 4:
            recommendation = "Strong Buy"
        elif net_signal >= 2:
            recommendation = "Buy"
        elif net_signal <= -4:
            recommendation = "Strong Sell"
        elif net_signal <= -2:
            recommendation = "Sell"
        else:
            recommendation = "Hold"
        
        return {
            'recommendation': recommendation,
            'bullish_signals': signals['bullish'],
            'bearish_signals': signals['bearish'],
            'net_signal': net_signal,
            'signal_details': signals['signals']
        }
    
    def _calculate_support_resistance(self, hist: pd.DataFrame, current_price: float) -> Dict[str, Any]:
        """Calculate professional support and resistance levels"""
        try:
            # 1. Swing highs/lows (local maxima/minima)
            swing_highs = self._find_swing_points(hist['High'], find_peaks=True)
            swing_lows = self._find_swing_points(hist['Low'], find_peaks=False)
            
            # 2. Volume profile (price levels with high volume)
            volume_levels = self._calculate_volume_profile(hist)
            
            # 3. Fibonacci retracements
            fibonacci = self._calculate_fibonacci_levels(hist)
            
            # 4. Pivot points
            pivots = self._calculate_pivot_points(hist)
            
            # 5. Moving average support/resistance
            ma_levels = self._get_ma_support_resistance(hist, current_price)
            
            # Combine and rank support levels
            support_candidates = swing_lows + volume_levels['support'] + ma_levels['support']
            support_levels = self._rank_levels(support_candidates, current_price, is_support=True)
            
            # Combine and rank resistance levels
            resistance_candidates = swing_highs + volume_levels['resistance'] + ma_levels['resistance']
            resistance_levels = self._rank_levels(resistance_candidates, current_price, is_support=False)
            
            return {
                'support_levels': support_levels[:3],  # Top 3
                'resistance_levels': resistance_levels[:3],  # Top 3
                'fibonacci': fibonacci,
                'pivot_points': pivots,
                'volume_clusters': volume_levels['clusters'],
                'swing_lows': swing_lows[:3],
                'swing_highs': swing_highs[:3]
            }
        except Exception as e:
            return {
                'support_levels': [],
                'resistance_levels': [],
                'fibonacci': {},
                'pivot_points': {},
                'volume_clusters': [],
                'swing_lows': [],
                'swing_highs': []
            }
    
    def _find_swing_points(self, series: pd.Series, find_peaks: bool = True, window: int = 5) -> list:
        """Find swing highs or lows using rolling window"""
        swings = []
        for i in range(window, len(series) - window):
            window_data = series.iloc[i-window:i+window+1]
            center_value = series.iloc[i]
            
            if find_peaks:
                if center_value == window_data.max():
                    swings.append(float(center_value))
            else:
                if center_value == window_data.min():
                    swings.append(float(center_value))
        
        # Return unique values sorted
        return sorted(list(set(swings)), reverse=not find_peaks)[:5]
    
    def _calculate_volume_profile(self, hist: pd.DataFrame, num_bins: int = 20) -> Dict[str, list]:
        """Calculate volume profile to find high-volume price levels"""
        try:
            # Create price bins
            price_min, price_max = hist['Low'].min(), hist['High'].max()
            bins = np.linspace(price_min, price_max, num_bins)
            
            # Aggregate volume by price bin
            volume_by_price = {}
            for _, row in hist.iterrows():
                bin_idx = np.digitize(row['Close'], bins) - 1
                if 0 <= bin_idx < len(bins) - 1:
                    price_level = (bins[bin_idx] + bins[bin_idx + 1]) / 2
                    volume_by_price[price_level] = volume_by_price.get(price_level, 0) + row['Volume']
            
            # Find top volume levels
            sorted_levels = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
            top_levels = [price for price, _ in sorted_levels[:5]]
            
            current_price = hist['Close'].iloc[-1]
            support = [p for p in top_levels if p < current_price]
            resistance = [p for p in top_levels if p > current_price]
            
            return {
                'support': support[:2],
                'resistance': resistance[:2],
                'clusters': top_levels[:3]
            }
        except:
            return {'support': [], 'resistance': [], 'clusters': []}
    
    def _calculate_fibonacci_levels(self, hist: pd.DataFrame, lookback: int = 50) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels from recent swing"""
        try:
            recent_data = hist.tail(lookback)
            swing_high = recent_data['High'].max()
            swing_low = recent_data['Low'].min()
            diff = swing_high - swing_low
            
            return {
                'level_0': float(swing_high),
                'level_23.6': float(swing_high - 0.236 * diff),
                'level_38.2': float(swing_high - 0.382 * diff),
                'level_50.0': float(swing_high - 0.500 * diff),
                'level_61.8': float(swing_high - 0.618 * diff),
                'level_78.6': float(swing_high - 0.786 * diff),
                'level_100': float(swing_low)
            }
        except:
            return {}
    
    def _calculate_pivot_points(self, hist: pd.DataFrame) -> Dict[str, float]:
        """Calculate standard pivot points from recent data"""
        try:
            recent = hist.tail(5)  # Last 5 days
            high = recent['High'].max()
            low = recent['Low'].min()
            close = recent['Close'].iloc[-1]
            
            pivot = (high + low + close) / 3
            r1 = 2 * pivot - low
            r2 = pivot + (high - low)
            s1 = 2 * pivot - high
            s2 = pivot - (high - low)
            
            return {
                'pivot': float(pivot),
                'r1': float(r1),
                'r2': float(r2),
                's1': float(s1),
                's2': float(s2)
            }
        except:
            return {}
    
    def _get_ma_support_resistance(self, hist: pd.DataFrame, current_price: float) -> Dict[str, list]:
        """Get moving averages as dynamic support/resistance"""
        support = []
        resistance = []
        
        for period in [20, 50, 200]:
            if len(hist) >= period:
                ma = hist['Close'].rolling(window=period).mean().iloc[-1]
                if ma < current_price:
                    support.append(float(ma))
                elif ma > current_price:
                    resistance.append(float(ma))
        
        return {'support': support, 'resistance': resistance}
    
    def _rank_levels(self, levels: list, current_price: float, is_support: bool, tolerance: float = 0.02) -> list:
        """Rank and filter support/resistance levels by proximity and strength"""
        if not levels:
            return []
        
        # Remove duplicates within tolerance
        unique_levels = []
        for level in sorted(levels):
            if not unique_levels or abs(level - unique_levels[-1]) / unique_levels[-1] > tolerance:
                unique_levels.append(level)
        
        # Filter by position relative to current price
        if is_support:
            filtered = [l for l in unique_levels if l < current_price]
            filtered.sort(reverse=True)  # Closest first
        else:
            filtered = [l for l in unique_levels if l > current_price]
            filtered.sort()  # Closest first
        
        return filtered
    
    def is_applicable(self, company_type: str) -> bool:
        """Technical analysis applies to all company types"""
        return True