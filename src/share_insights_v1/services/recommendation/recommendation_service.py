from typing import Dict, List, Optional
from dataclasses import dataclass
from ...interfaces.recommendation_engine import IRecommendationEngine
from ...models.analysis_result import AnalysisResult
from ...models.recommendation import Recommendation, RecommendationType
from ...models.company import Company

@dataclass
class ConsolidatedRecommendation:
    """Consolidated recommendation from multiple analyzers"""
    final_recommendation: RecommendationType
    confidence_level: str
    consensus_score: float
    individual_recommendations: Dict[str, RecommendationType]
    price_targets: Dict[str, float]
    key_insights: List[str]

class RecommendationService(IRecommendationEngine):
    """Service to consolidate recommendations from multiple analyzers"""
    
    def __init__(self):
        self.recommendation_weights = {
            'dcf': 0.25,
            'comparable': 0.2,
            'technical': 0.15,
            'startup': 0.4,
            'analyst_consensus': 0.25,
            'ai_insights': 0.15
        }
    
    def generate_recommendation(self, company: Company, analyses: Dict[str, AnalysisResult]) -> Recommendation:
        """Generate consolidated recommendation from multiple analyses"""
        consolidated = self._consolidate_recommendations(analyses)
        
        return Recommendation(
            ticker=company.ticker,
            recommendation=consolidated.final_recommendation,
            confidence=consolidated.confidence_level,
            target_price=self._get_consensus_target_price(consolidated.price_targets),
            upside_potential=self._calculate_upside_potential(analyses),
            risk_level=self._determine_risk_level(analyses),
            bullish_signals=self._extract_bullish_signals(analyses),
            bearish_signals=self._extract_bearish_signals(analyses),
            key_risks=self._identify_risk_factors(analyses),
            summary=self._build_reasoning(consolidated)
        )
    
    def _consolidate_recommendations(self, analyses: Dict[str, AnalysisResult]) -> ConsolidatedRecommendation:
        """Consolidate individual analyzer recommendations"""
        recommendations = {}
        price_targets = {}
        
        for analysis_type, result in analyses.items():
            if isinstance(result, dict) and 'recommendation' in result:
                recommendations[analysis_type] = RecommendationType(result['recommendation'])
            if isinstance(result, dict) and 'predicted_price' in result:
                price_targets[analysis_type] = result['predicted_price']
        
        consensus_score = self._calculate_consensus_score(recommendations)
        final_recommendation = self._determine_final_recommendation(recommendations, consensus_score)
        confidence = self._determine_confidence(consensus_score, len(recommendations))
        
        return ConsolidatedRecommendation(
            final_recommendation=final_recommendation,
            confidence_level=confidence,
            consensus_score=consensus_score,
            individual_recommendations=recommendations,
            price_targets=price_targets,
            key_insights=self._extract_key_insights(analyses)
        )
    
    def _calculate_consensus_score(self, recommendations: Dict[str, RecommendationType]) -> float:
        """Calculate consensus score based on recommendation alignment"""
        if not recommendations:
            return 0.0
        
        score_map = {
            RecommendationType.STRONG_BUY: 2,
            RecommendationType.BUY: 1,
            RecommendationType.SPECULATIVE_BUY: 1,
            RecommendationType.HOLD: 0,
            RecommendationType.MONITOR: 0,
            RecommendationType.SELL: -1,
            RecommendationType.STRONG_SELL: -2
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for analysis_type, recommendation in recommendations.items():
            weight = self.recommendation_weights.get(analysis_type, 0.1)
            weighted_score += score_map[recommendation] * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _determine_final_recommendation(self, recommendations: Dict[str, RecommendationType], consensus_score: float) -> RecommendationType:
        """Determine final recommendation based on consensus score"""
        if consensus_score >= 1.5:
            return RecommendationType.STRONG_BUY
        elif consensus_score >= 0.5:
            return RecommendationType.BUY
        elif consensus_score <= -1.5:
            return RecommendationType.STRONG_SELL
        elif consensus_score <= -0.5:
            return RecommendationType.SELL
        else:
            return RecommendationType.HOLD
    
    def _determine_confidence(self, consensus_score: float, num_analyses: int) -> str:
        """Determine confidence level based on consensus and number of analyses"""
        agreement_strength = abs(consensus_score)
        
        if num_analyses >= 3 and agreement_strength >= 1.0:
            return "High"
        elif num_analyses >= 2 and agreement_strength >= 0.5:
            return "Medium"
        else:
            return "Low"
    
    def _get_consensus_target_price(self, price_targets: Dict[str, float]) -> Optional[float]:
        """Calculate weighted consensus target price"""
        if not price_targets:
            return None
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for analysis_type, target_price in price_targets.items():
            weight = self.recommendation_weights.get(analysis_type, 0.1)
            weighted_sum += target_price * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else None
    
    def _build_reasoning(self, consolidated: ConsolidatedRecommendation) -> str:
        """Build reasoning text for the recommendation"""
        reasoning_parts = [
            f"Consensus: {consolidated.final_recommendation.value}",
            f"Confidence: {consolidated.confidence_level}",
            f"Analyses: {len(consolidated.individual_recommendations)}"
        ]
        
        for analysis_type, recommendation in consolidated.individual_recommendations.items():
            reasoning_parts.append(f"{analysis_type.upper()}: {recommendation.value}")
        
        return " | ".join(reasoning_parts)
    
    def _identify_risk_factors(self, analyses: Dict[str, AnalysisResult]) -> List[str]:
        """Identify key risk factors from analyses"""
        risk_factors = []
        
        for analysis_type, result in analyses.items():
            if isinstance(result, dict):
                if result.get('confidence') == "Low":
                    risk_factors.append(f"Low confidence in {analysis_type} analysis")
                
                if analysis_type == 'technical' and 'volatility_annual' in result:
                    if result['volatility_annual'] > 0.5:
                        risk_factors.append("High volatility")
        
        return risk_factors
    
    def _extract_key_insights(self, analyses: Dict[str, AnalysisResult]) -> List[str]:
        """Extract key insights from analyses"""
        insights = []
        
        for analysis_type, result in analyses.items():
            if isinstance(result, dict) and 'valuation' in result:
                insights.append(f"{analysis_type.upper()}: {result['valuation']}")
        
        return insights
    
    def _calculate_upside_potential(self, analyses: Dict[str, AnalysisResult]) -> Optional[float]:
        """Calculate upside potential based on consensus target price vs current price"""
        current_price = None
        for result in analyses.values():
            if isinstance(result, dict) and 'current_price' in result:
                current_price = result['current_price']
                break
        
        if not current_price:
            return None
            
        price_targets = {}
        for analysis_type, result in analyses.items():
            if isinstance(result, dict) and 'predicted_price' in result:
                price_targets[analysis_type] = result['predicted_price']
        
        consensus_target = self._get_consensus_target_price(price_targets)
        if consensus_target:
            return ((consensus_target - current_price) / current_price) * 100
        return None
    
    def _determine_risk_level(self, analyses: Dict[str, AnalysisResult]) -> str:
        """Determine overall risk level"""
        high_risk_count = 0
        total_analyses = len(analyses)
        
        for analysis_type, result in analyses.items():
            if isinstance(result, dict):
                if analysis_type == 'technical' and 'volatility_annual' in result:
                    if result['volatility_annual'] > 0.5:
                        high_risk_count += 1
                if result.get('confidence') == 'Low':
                    high_risk_count += 1
        
        if high_risk_count >= total_analyses * 0.5:
            return "High"
        elif high_risk_count > 0:
            return "Medium"
        else:
            return "Low"
    
    def _extract_bullish_signals(self, analyses: Dict[str, AnalysisResult]) -> List[str]:
        """Extract bullish signals from analyses"""
        signals = []
        for analysis_type, result in analyses.items():
            if isinstance(result, dict):
                if result.get('recommendation') in ['Strong Buy', 'Buy']:
                    signals.append(f"{analysis_type.upper()} indicates {result.get('recommendation')}")
                if analysis_type == 'technical' and 'trend' in result:
                    if 'Uptrend' in result['trend']:
                        signals.append(f"Technical: {result['trend']}")
        return signals
    
    def _extract_bearish_signals(self, analyses: Dict[str, AnalysisResult]) -> List[str]:
        """Extract bearish signals from analyses"""
        signals = []
        for analysis_type, result in analyses.items():
            if isinstance(result, dict):
                if result.get('recommendation') in ['Strong Sell', 'Sell']:
                    signals.append(f"{analysis_type.upper()} indicates {result.get('recommendation')}")
                if result.get('valuation') == 'Overvalued':
                    signals.append(f"{analysis_type.upper()}: Overvalued")
        return signals