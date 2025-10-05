from typing import Dict, Any, List
from dataclasses import dataclass
from ...interfaces.data_provider import IDataProvider

@dataclass
class ComparisonResult:
    """Result of comparing our analysis with professional analysts"""
    ticker: str
    method: str
    our_price: float
    analyst_target: float
    current_price: float
    our_upside: float
    analyst_upside: float
    deviation_score: float
    alignment: str
    both_bullish: bool
    both_bearish: bool
    analyst_count: int

class AnalystComparisonService:
    """Service to compare our analysis results against professional analyst consensus"""
    
    def __init__(self, data_provider: IDataProvider):
        self.data_provider = data_provider
    
    def compare_analysis_results(self, ticker: str, analysis_results: Dict[str, Any]) -> List[ComparisonResult]:
        """Compare our analysis results against professional analyst consensus"""
        try:
            analyst_data = self.data_provider.get_professional_analyst_data(ticker)
            
            if 'error' in analyst_data or not analyst_data.get('target_price'):
                return []
            
            analyst_target = analyst_data.get('target_price')
            analyst_count = analyst_data.get('analyst_count', 0)
            current_price = analysis_results.get('financial_metrics', {}).get('current_price', 0)
            
            if not current_price:
                return []
            
            comparisons = []
            
            for method, result in analysis_results.get('analyses', {}).items():
                if isinstance(result, dict) and 'predicted_price' in result:
                    our_price = result['predicted_price']
                    
                    if our_price and our_price > 0:
                        comparison = self._calculate_deviation(
                            our_price, analyst_target, current_price, analyst_count
                        )
                        comparison.ticker = ticker
                        comparison.method = method
                        comparisons.append(comparison)
            
            return comparisons
            
        except Exception as e:
            return []
    
    def _calculate_deviation(self, our_price: float, analyst_target: float, 
                           current_price: float, analyst_count: int) -> ComparisonResult:
        """Calculate deviation between our analysis and analyst consensus"""
        
        our_upside = ((our_price - current_price) / current_price) * 100
        analyst_upside = ((analyst_target - current_price) / current_price) * 100
        deviation_score = abs(our_upside - analyst_upside)
        alignment = self._determine_alignment(deviation_score, our_upside, analyst_upside)
        both_bullish = our_upside > 5 and analyst_upside > 5
        both_bearish = our_upside < -5 and analyst_upside < -5
        
        return ComparisonResult(
            ticker="",
            method="",
            our_price=our_price,
            analyst_target=analyst_target,
            current_price=current_price,
            our_upside=our_upside,
            analyst_upside=analyst_upside,
            deviation_score=deviation_score,
            alignment=alignment,
            both_bullish=both_bullish,
            both_bearish=both_bearish,
            analyst_count=analyst_count
        )
    
    def _determine_alignment(self, deviation_score: float, our_upside: float, analyst_upside: float) -> str:
        """Determine alignment category based on deviation and direction"""
        # Check if predictions are in opposite directions
        if (our_upside > 0 and analyst_upside < 0) or (our_upside < 0 and analyst_upside > 0):
            return "Divergent"
        
        # Same direction - classify by deviation magnitude
        if deviation_score <= 5:
            return "Precise_Aligned"
        elif deviation_score <= 15:
            if (our_upside > 0 and analyst_upside > 0) or (our_upside < 0 and analyst_upside < 0):
                return "Investment_Aligned"
            else:
                return "Divergent"
        else:
            return "Directional_Aligned"
    
    def generate_comparison_summary(self, comparisons: List[ComparisonResult]) -> Dict[str, Any]:
        """Generate summary statistics for comparison results"""
        if not comparisons:
            return {}
        
        method_stats = {}
        methods = set(comp.method for comp in comparisons)
        
        for method in methods:
            method_comps = [c for c in comparisons if c.method == method]
            
            if method_comps:
                aligned = len([c for c in method_comps if c.alignment != 'Divergent'])
                bullish_convergent = len([c for c in method_comps if c.both_bullish])
                avg_deviation = sum(c.deviation_score for c in method_comps) / len(method_comps)
                
                method_stats[method] = {
                    'total_comparisons': len(method_comps),
                    'aligned_count': aligned,
                    'bullish_convergent': bullish_convergent,
                    'alignment_rate': (aligned / len(method_comps)) * 100,
                    'avg_deviation': avg_deviation
                }
        
        return method_stats