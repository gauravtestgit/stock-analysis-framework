from typing import Dict, Optional
import json
from datetime import datetime
from .stock_analyzer import StockAnalyzer, FinanceConfig
from .ai_data_retriever import AIDataRetriever
from .ai_analyzer import AIAnalyzer

class AIEnhancedStockAnalyzer:
    """Enhanced stock analyzer that combines quantitative analysis with AI insights"""
    
    def __init__(self, ticker: str, config: Optional[FinanceConfig] = None):
        self.ticker = ticker.upper()
        self.config = config or FinanceConfig()
        
        # Initialize components
        self.stock_analyzer = StockAnalyzer(ticker, config)
        self.ai_retriever = AIDataRetriever()
        self.ai_analyzer = AIAnalyzer()
        
    def run_enhanced_analysis(self) -> Dict:
        """Run complete analysis with AI enhancement"""
        print(f"\n=== ENHANCED ANALYSIS FOR {self.ticker} ===")
        
        # Step 1: Run traditional quantitative analysis
        print("1. Running quantitative analysis...")
        quant_analysis = self.stock_analyzer.comprehensive_analysis()
        
        # Step 2: Retrieve AI data
        print("2. Retrieving financial results, earnings, and news...")
        ai_data = self.ai_retriever.get_comprehensive_data(self.ticker)
        
        # Step 3: Generate AI insights
        print("3. Generating AI insights...")
        # Combine AI data with financial metrics from quantitative analysis
        enhanced_ai_data = ai_data.copy()
        financial_metrics = quant_analysis.get('financial_metrics', {}).copy()
        
        # Override quarterly revenue growth with AI calculated value if available
        earnings_data = ai_data.get('earnings_data', {})
        if earnings_data.get('revenue_growth'):
            # Extract percentage from string like "-20.6%"
            revenue_growth_str = earnings_data['revenue_growth']
            if '%' in revenue_growth_str:
                try:
                    quarterly_growth = float(revenue_growth_str.replace('%', '')) / 100
                    financial_metrics['quarterly_revenue_growth'] = quarterly_growth
                except ValueError:
                    pass
        
        enhanced_ai_data['financial_metrics'] = financial_metrics
        ai_insights = self.ai_analyzer.generate_ai_insights(enhanced_ai_data)
        
        # Step 4: Combine and enhance analysis
        print("4. Combining quantitative and AI analysis...")
        enhanced_analysis = self._combine_analyses(quant_analysis, ai_insights, ai_data)
        
        return enhanced_analysis
    
    def _combine_analyses(self, quant_analysis: Dict, ai_insights: Dict, ai_data: Dict) -> Dict:
        """Combine quantitative analysis with AI insights"""
        
        # Start with quantitative analysis as base
        enhanced = {
            'ticker': self.ticker,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'analysis_type': 'AI-Enhanced',
            
            # Original quantitative analysis
            'quantitative_analysis': {
                'company_type': quant_analysis.get('company_type'),
                'financial_metrics': quant_analysis.get('financial_metrics'),
                'quality_score': quant_analysis.get('quality_score'),
                'dcf_analysis': quant_analysis.get('dcf_analysis'),
                'technical_analysis': quant_analysis.get('technical_analysis'),
                'comparable_analysis': quant_analysis.get('comparable_analysis'),
                'startup_analysis': quant_analysis.get('startup_analysis'),
                'professional_analysis': quant_analysis.get('professional_analysis'),
                'original_summary': quant_analysis.get('summary')
            },
            
            # AI enhancement data
            'ai_enhancement': {
                'data_quality': ai_data.get('data_quality'),
                'earnings_analysis': ai_insights.get('earnings_analysis'),
                'news_sentiment': ai_insights.get('news_sentiment'),
                'overall_assessment': ai_insights.get('overall_assessment'),
                'risk_flags': ai_insights.get('risk_flags'),
                'recommendation_adjustments': ai_insights.get('recommendation_adjustments'),
                'recent_news': ai_data.get('recent_news', [])[:5]
            },
            
            # Enhanced recommendation
            'enhanced_recommendation': self._generate_enhanced_recommendation(quant_analysis, ai_insights)
        }
        
        return enhanced
    
    def _generate_enhanced_recommendation(self, quant_analysis: Dict, ai_insights: Dict) -> Dict:
        """Generate enhanced recommendation combining quant and AI insights"""
        
        # Get original recommendation
        original_summary = quant_analysis.get('summary', {})
        original_rec = original_summary.get('recommendation', 'HOLD')
        original_confidence = original_summary.get('confidence', 'Medium')
        
        # Get AI assessment
        ai_assessment = ai_insights.get('overall_assessment', {})
        ai_confidence = ai_assessment.get('confidence_level', 'Medium')
        risk_flags = ai_insights.get('risk_flags', [])
        
        # Determine adjustment direction
        adjustment_direction = self._determine_adjustment_direction(ai_insights)
        
        # Generate enhanced recommendation
        enhanced_rec = {
            'original_recommendation': original_rec,
            'ai_adjustment': adjustment_direction,
            'final_recommendation': self._adjust_recommendation(original_rec, adjustment_direction),
            'confidence_level': self._combine_confidence(original_confidence, ai_confidence, risk_flags),
            'key_factors': self._identify_key_factors(quant_analysis, ai_insights),
            'risk_assessment': self._enhanced_risk_assessment(original_summary, ai_insights),
            'investment_thesis': self._generate_enhanced_thesis(quant_analysis, ai_insights),
            'action_items': self._generate_action_items(ai_insights)
        }
        
        return enhanced_rec
    
    def _determine_adjustment_direction(self, ai_insights: Dict) -> str:
        """Determine if AI insights suggest upgrading or downgrading recommendation"""
        
        earnings_analysis = ai_insights.get('earnings_analysis', {})
        news_sentiment = ai_insights.get('news_sentiment', {})
        risk_flags = ai_insights.get('risk_flags', [])
        
        positive_signals = 0
        negative_signals = 0
        
        # Enhanced earnings signals - consider both annual and quarterly trends
        revenue_assessment = earnings_analysis.get('revenue_assessment', 'Unknown')
        annual_growth = earnings_analysis.get('annual_revenue_growth', 0)
        quarterly_growth = earnings_analysis.get('quarterly_revenue_growth', 0)
        
        # If annual growth is positive but quarterly is negative, treat as mixed signal
        if revenue_assessment in ['Declining'] and annual_growth > 0.1:  # >10% annual growth
            # Short-term decline with strong annual growth - neutral to slightly negative
            negative_signals += 1  # Reduced from 2
            positive_signals += 0.5  # Add some positive weight for annual growth
        elif revenue_assessment in ['Excellent', 'Good']:
            positive_signals += 2
        elif revenue_assessment in ['Weak', 'Declining']:
            negative_signals += 2
        
        surprise_impact = earnings_analysis.get('surprise_impact', 'Neutral')
        if surprise_impact == 'Positive':
            positive_signals += 1
        elif surprise_impact == 'Negative':
            negative_signals += 1
        
        # News sentiment signals
        overall_sentiment = news_sentiment.get('overall_sentiment', 'Neutral')
        if overall_sentiment == 'Positive':
            positive_signals += 1
        elif overall_sentiment == 'Negative':
            negative_signals += 1
        
        # Risk flags
        if len(risk_flags) >= 2:
            negative_signals += 2
        elif len(risk_flags) == 1:
            negative_signals += 1
        
        # Determine adjustment with more nuanced logic
        signal_difference = negative_signals - positive_signals
        
        # Check AI recommendation directly for override
        ai_recommendation = ai_insights.get('overall_assessment', {}).get('ai_recommendation', '')
        if ai_recommendation == 'MAINTAIN' and signal_difference <= 2:
            return 'MAINTAIN'  # Trust AI assessment for borderline cases
        
        if positive_signals > negative_signals + 1:
            return 'UPGRADE'
        elif negative_signals > positive_signals + 1.5:  # Slightly higher threshold
            return 'DOWNGRADE'
        else:
            return 'MAINTAIN'
    
    def _adjust_recommendation(self, original_rec: str, adjustment: str) -> str:
        """Adjust recommendation based on AI insights"""
        
        if adjustment == 'MAINTAIN':
            return original_rec
        
        # Define recommendation hierarchy
        rec_hierarchy = ['AVOID', 'SELL', 'HOLD', 'BUY', 'STRONG BUY', 'SPECULATIVE BUY']
        
        try:
            current_index = rec_hierarchy.index(original_rec)
        except ValueError:
            return original_rec  # If recommendation not in hierarchy, return as-is
        
        if adjustment == 'UPGRADE':
            new_index = min(current_index + 1, len(rec_hierarchy) - 1)
        else:  # DOWNGRADE
            new_index = max(current_index - 1, 0)
        
        return rec_hierarchy[new_index]
    
    def _combine_confidence(self, original_confidence: str, ai_confidence: str, risk_flags: list) -> str:
        """Combine confidence levels from quantitative and AI analysis"""
        
        confidence_scores = {'Low': 1, 'Medium': 2, 'High': 3}
        
        orig_score = confidence_scores.get(original_confidence, 2)
        ai_score = confidence_scores.get(ai_confidence, 2)
        
        # Average the scores
        combined_score = (orig_score + ai_score) / 2
        
        # Reduce confidence if there are risk flags
        if len(risk_flags) >= 2:
            combined_score -= 0.5
        elif len(risk_flags) == 1:
            combined_score -= 0.25
        
        # Convert back to confidence level
        if combined_score >= 2.5:
            return 'High'
        elif combined_score >= 1.5:
            return 'Medium'
        else:
            return 'Low'
    
    def _identify_key_factors(self, quant_analysis: Dict, ai_insights: Dict) -> list:
        """Identify key factors driving the enhanced recommendation"""
        
        factors = []
        
        # Add quantitative factors
        original_summary = quant_analysis.get('summary', {})
        quant_signals = original_summary.get('signals', {})
        
        if quant_signals.get('bullish'):
            factors.extend([f"Quant: {signal}" for signal in quant_signals['bullish'][:2]])
        if quant_signals.get('bearish'):
            factors.extend([f"Quant: {signal}" for signal in quant_signals['bearish'][:2]])
        
        # Add AI factors
        earnings_analysis = ai_insights.get('earnings_analysis', {})
        if earnings_analysis.get('key_insights'):
            factors.extend([f"AI: {insight}" for insight in earnings_analysis['key_insights'][:2]])
        
        news_sentiment = ai_insights.get('news_sentiment', {})
        if news_sentiment.get('overall_sentiment') != 'Neutral':
            factors.append(f"AI: {news_sentiment['overall_sentiment']} market sentiment")
        
        return factors[:5]  # Limit to top 5 factors
    
    def _enhanced_risk_assessment(self, original_summary: Dict, ai_insights: Dict) -> Dict:
        """Enhanced risk assessment combining quantitative and AI insights"""
        
        original_risks = original_summary.get('key_risks', [])
        ai_risk_flags = ai_insights.get('risk_flags', [])
        
        return {
            'quantitative_risks': original_risks,
            'ai_identified_risks': ai_risk_flags,
            'combined_risk_level': original_summary.get('risk_level', 'Medium'),
            'risk_mitigation': self._suggest_risk_mitigation(ai_risk_flags)
        }
    
    def _suggest_risk_mitigation(self, risk_flags: list) -> list:
        """Suggest risk mitigation strategies"""
        
        mitigation = []
        
        if 'Revenue decline trend' in risk_flags:
            mitigation.append("Monitor quarterly results closely for turnaround signs")
        
        if 'Recent earnings miss' in risk_flags:
            mitigation.append("Wait for next earnings to confirm if miss was one-time")
        
        if 'Negative media coverage' in risk_flags:
            mitigation.append("Assess if negative news reflects fundamental issues")
        
        if 'Multiple negative news stories' in risk_flags:
            mitigation.append("Consider reducing position size until sentiment improves")
        
        return mitigation
    
    def _generate_enhanced_thesis(self, quant_analysis: Dict, ai_insights: Dict) -> str:
        """Generate enhanced investment thesis"""
        
        company_type = quant_analysis.get('company_type', 'Unknown')
        quality_grade = quant_analysis.get('quality_score', {}).get('quality_grade', 'C')
        
        ai_assessment = ai_insights.get('overall_assessment', {})
        ai_summary = ai_assessment.get('summary', 'Mixed signals')
        
        earnings_assessment = ai_insights.get('earnings_analysis', {}).get('revenue_assessment', 'Unknown')
        news_sentiment = ai_insights.get('news_sentiment', {}).get('overall_sentiment', 'Neutral')
        
        thesis = f"{company_type.replace('_', ' ').title()} company with {quality_grade} quality metrics. "
        thesis += f"Recent financial performance shows {earnings_assessment.lower()} revenue trends. "
        thesis += f"Market sentiment is {news_sentiment.lower()}. "
        thesis += f"AI assessment: {ai_summary.lower()}."
        
        return thesis
    
    def _generate_action_items(self, ai_insights: Dict) -> list:
        """Generate specific action items based on AI insights"""
        
        actions = []
        
        # Actions based on earnings
        earnings_analysis = ai_insights.get('earnings_analysis', {})
        if earnings_analysis.get('revenue_assessment') == 'Declining':
            actions.append("Monitor next 2 quarters for revenue stabilization")
        
        # Actions based on news
        news_sentiment = ai_insights.get('news_sentiment', {})
        if news_sentiment.get('overall_sentiment') == 'Negative':
            actions.append("Track resolution of issues mentioned in recent news")
        
        # Actions based on risk flags
        risk_flags = ai_insights.get('risk_flags', [])
        if risk_flags:
            actions.append(f"Address {len(risk_flags)} identified risk factors")
        
        # General actions
        actions.append("Review analysis after next earnings announcement")
        
        return actions

# Test function
def test_enhanced_analyzer(ticker: str = "AAPL"):
    """Test the enhanced analyzer"""
    
    print(f"Testing AI-Enhanced Analysis for {ticker}")
    
    analyzer = AIEnhancedStockAnalyzer(ticker)
    enhanced_analysis = analyzer.run_enhanced_analysis()
    
    # Display results
    enhanced_rec = enhanced_analysis['enhanced_recommendation']
    
    print(f"\n=== ENHANCED ANALYSIS RESULTS ===")
    print(f"Original Recommendation: {enhanced_rec['original_recommendation']}")
    print(f"AI Adjustment: {enhanced_rec['ai_adjustment']}")
    print(f"Final Recommendation: {enhanced_rec['final_recommendation']}")
    print(f"Confidence Level: {enhanced_rec['confidence_level']}")
    print(f"Investment Thesis: {enhanced_rec['investment_thesis']}")
    
    print(f"\nKey Factors:")
    for factor in enhanced_rec['key_factors']:
        print(f"  • {factor}")
    
    if enhanced_rec['risk_assessment']['ai_identified_risks']:
        print(f"\nAI-Identified Risks:")
        for risk in enhanced_rec['risk_assessment']['ai_identified_risks']:
            print(f"  • {risk}")
    
    print(f"\nAction Items:")
    for action in enhanced_rec['action_items']:
        print(f"  • {action}")
    
    # Save results
    filedir = "C:/Users/x_gau/source/repos/agentic/langchain/tutorials/finance-app/src/financial_analyst/output/ai_analysis/"
    filename = filedir+f'enhanced_analysis_{ticker.lower()}.json'
    with open(filename, 'w') as f:
        json.dump(enhanced_analysis, f, indent=2, default=str)
    
    print(f"\nEnhanced analysis saved to {filename}")
    return enhanced_analysis

if __name__ == "__main__":
    import sys
    
    # Get ticker from command line args or use default
    symbols = sys.argv[1:] if len(sys.argv) > 1 else "aapl"
    for symbol in symbols:
        ticker = symbol.strip().upper()
        test_enhanced_analyzer(ticker)