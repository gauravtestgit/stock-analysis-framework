#!/usr/bin/env python3

import sys
import os

from ..implementations.analyzers.revenue_stream_analyzer import RevenueStreamAnalyzer
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..services.orchestration.analysis_orchestrator import AnalysisOrchestrator
from ..implementations.classifier import CompanyClassifier
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..models.analysis_result import AnalysisType

def test_revenue_stream_analyzer():
    """Test revenue stream analyzer"""
    
    # Initialize components
    data_provider = YahooFinanceProvider()
    classifier = CompanyClassifier()
    quality_calculator = QualityScoreCalculator()
    orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator)
    
    # Register revenue stream analyzer
    revenue_analyzer = RevenueStreamAnalyzer()
    orchestrator.register_analyzer(AnalysisType.REVENUE_STREAM, revenue_analyzer)
    
    # Test with different company types
    test_tickers = ['AAPL', 'MSFT', 'AMZN']  # Tech companies with different revenue models
    
    for ticker in test_tickers:
        print(f"\n=== Testing Revenue Stream Analysis for {ticker} ===")
        
        try:
            # Get financial data
            financial_metrics = data_provider.get_financial_metrics(ticker)
            price_data = data_provider.get_price_data(ticker)
            
            if 'error' in financial_metrics:
                print(f"Error getting data for {ticker}: {financial_metrics['error']}")
                continue
            
            # Prepare analysis data
            analysis_data = {
                'financial_metrics': financial_metrics,
                'price_data': price_data,
                'company_info': {
                    'sector': financial_metrics.get('sector', ''),
                    'industry': financial_metrics.get('industry', ''),
                },
                'current_price': financial_metrics.get('current_price', 0)
            }
            
            # Run revenue stream analysis
            result = revenue_analyzer.analyze(ticker, analysis_data)
            
            if 'error' in result:
                print(f"Analysis error: {result['error']}")
                continue
            
            # Display results
            print(f"Method: {result.get('method', 'N/A')}")
            print(f"Sector: {result.get('sector', 'N/A')}")
            print(f"Industry: {result.get('industry', 'N/A')}")
            print(f"Recommendation: {result.get('recommendation', 'N/A')}")
            
            # Revenue streams
            revenue_streams = result.get('revenue_streams', {})
            print(f"\nRevenue Analysis:")
            print(f"  Revenue Model: {revenue_streams.get('revenue_model', 'N/A')}")
            print(f"  Total Revenue (TTM): ${revenue_streams.get('total_revenue_ttm', 0):,.0f}")
            print(f"  Revenue Growth (YoY): {revenue_streams.get('revenue_growth_yoy', 0):.1f}%")
            
            # Market analysis
            market_analysis = result.get('market_analysis', {})
            print(f"\nMarket Analysis:")
            print(f"  Market Sensitivity: {market_analysis.get('market_sensitivity', 'N/A')}")
            print(f"  Average Correlation: {market_analysis.get('average_correlation', 0):.2f}")
            
            # Earnings forecast
            earnings_forecast = result.get('earnings_forecast', {})
            print(f"\nEarnings Forecast:")
            print(f"  Current Revenue: ${earnings_forecast.get('current_revenue', 0):,.0f}")
            print(f"  Estimated Revenue (1Y): ${earnings_forecast.get('estimated_revenue_1y', 0):,.0f}")
            print(f"  Growth Rate Estimate: {earnings_forecast.get('growth_rate_estimate', 0):.1f}%")
            print(f"  Confidence Level: {earnings_forecast.get('confidence_level', 0):.1%}")
            
            # Revenue insights
            revenue_insights = result.get('revenue_insights', {})
            if revenue_insights and 'error' not in revenue_insights:
                print(f"\nRevenue Insights:")
                for key, value in revenue_insights.items():
                    print(f"  {key.replace('_', ' ').title()}: {value}")
            
        except Exception as e:
            print(f"Test failed for {ticker}: {str(e)}")

if __name__ == "__main__":
    test_revenue_stream_analyzer()