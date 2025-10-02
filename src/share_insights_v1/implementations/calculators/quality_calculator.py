from typing import Dict, Any
from ...interfaces.calculator import ICalculator
from ...models.quality_score import QualityScore

class QualityScoreCalculator(ICalculator):
    """Company quality score calculator"""
    
    def calculate(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate company quality score"""
        try:
            score = 0
            missing_penalty = 0
            
            # Profitability (25 points)
            roe = metrics.get('roe')
            if roe is not None:
                if roe > 0.15:
                    score += 15
                elif roe > 0.10:
                    score += 10
                elif roe > 0.05:
                    score += 5
            else:
                missing_penalty += 3
                
            net_income = metrics.get('net_income', 0)
            if net_income and net_income > 0:
                score += 10
            
            # Financial Health (25 points)
            debt_equity = metrics.get('debt_to_equity')
            if debt_equity is not None:
                if debt_equity < 0.3:
                    score += 15
                elif debt_equity < 0.6:
                    score += 10
                elif debt_equity < 1.0:
                    score += 5
            else:
                missing_penalty += 2
            
            # Growth (25 points)
            revenue_growth = metrics.get('yearly_revenue_growth')
            if revenue_growth is not None:
                if revenue_growth > 0.20:
                    score += 15
                elif revenue_growth > 0.10:
                    score += 10
                elif revenue_growth > 0.05:
                    score += 5
            else:
                missing_penalty += 2
            
            # Valuation (25 points)
            pe_ratio = metrics.get('pe_ratio')
            if pe_ratio is not None and pe_ratio > 0:
                if 10 < pe_ratio < 20:
                    score += 15
                elif 8 < pe_ratio < 25:
                    score += 10
                elif pe_ratio < 30:
                    score += 5
            else:
                missing_penalty += 2
            
            final_score = max(0, score - missing_penalty)
            data_quality = "High" if missing_penalty <= 3 else "Medium" if missing_penalty <= 7 else "Low"
            
            quality_score = QualityScore(
                score=final_score,
                missing_data_penalty=missing_penalty,
                data_quality=data_quality
            )
            
            return {
                'quality_score': quality_score.score,
                'grade': quality_score.grade,
                'data_quality': quality_score.data_quality,
                'missing_penalty': quality_score.missing_data_penalty
            }
            
        except Exception as e:
            return {'error': str(e)}