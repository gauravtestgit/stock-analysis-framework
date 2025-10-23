from typing import Dict, Any, Optional
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
from ...models.analysis_result import AnalysisResult, AnalysisType
from ...models.recommendation import RecommendationType

class AnalystConsensusAnalyzer(IAnalyzer):
    """Analyzer for professional analyst consensus data"""
    
    def __init__(self, data_provider: IDataProvider):
        self.data_provider = data_provider
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze professional analyst consensus"""
        try:
            analyst_data = self.data_provider.get_professional_analyst_data(ticker)
            
            if 'error' in analyst_data:
                return {'error': f"Failed to get analyst data: {analyst_data['error']}"}
            
            current_price = data.get('current_price', 0)
            
            # Get current price from price data if not available in financial metrics
            if not current_price:
                financial_metrics = data.get('financial_metrics', {})
                current_price = financial_metrics.get('current_price', 0)
                
                if not current_price:
                    price_data = data.get('price_data', {})
                    price_history = price_data.get('price_history')
                    if price_history is not None and not price_history.empty:
                        current_price = price_history['Close'].iloc[-1]
            
            # Extract key metrics
            target_mean = analyst_data.get('target_price')
            target_high = analyst_data.get('target_high')
            target_low = analyst_data.get('target_low')
            recommendation_mean = analyst_data.get('recommendation')
            num_analysts = analyst_data.get('analyst_count', 0)
            
            # Calculate upside potential
            upside_pct = None
            if target_mean and current_price:
                upside_pct = ((target_mean - current_price) / current_price) * 100
            
            # Convert recommendation mean to recommendation type
            recommendation = self._convert_recommendation_mean(recommendation_mean)
            
            # Determine confidence based on number of analysts
            confidence = self._determine_confidence(num_analysts)
            
            return {
                'method': 'Professional Analyst Consensus',
                'applicable': True,
                'current_price': current_price,
                'predicted_price': target_mean,
                'target_high': target_high,
                'target_low': target_low,
                'upside_downside_pct': upside_pct,
                'recommendation': recommendation,
                'recommendation_mean': recommendation_mean,
                'num_analysts': num_analysts,
                'confidence': confidence,
                'analysis_type': 'analyst_consensus'
            }
            
        except Exception as e:
            return {'error': f"Analyst consensus analysis failed: {str(e)}"}
    
    def _convert_recommendation_mean(self, rec_mean: float) -> str:
        """Convert Yahoo's recommendation mean to recommendation type"""
        if not rec_mean:
            return "Hold"
        
        # Yahoo scale: 1=Strong Buy, 2=Buy, 3=Hold, 4=Sell, 5=Strong Sell
        if rec_mean <= 1.5:
            return "Strong Buy"
        elif rec_mean <= 2.5:
            return "Buy"
        elif rec_mean <= 3.5:
            return "Hold"
        elif rec_mean <= 4.5:
            return "Sell"
        else:
            return "Strong Sell"
    
    def _determine_confidence(self, num_analysts: int) -> str:
        """Determine confidence based on number of analysts"""
        if num_analysts >= 10:
            return "High"
        elif num_analysts >= 5:
            return "Medium"
        else:
            return "Low"
    
    def is_applicable(self, company_type: str) -> bool:
        """Analyst consensus applicable to most public companies"""
        return True
        # return company_type != "startup_loss_making"  # Startups typically don't have analyst coverage