#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ..implementations.data_providers.sec_edgar_provider import SECEdgarProvider
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.analyzers.business_model_analyzer import BusinessModelAnalyzer
from ..implementations.llm_providers.llm_manager import LLMManager

def test_business_model_analyzer():
    """Test Business Model Analyzer with enhanced revenue stream analysis"""
    
    print("Testing Enhanced Business Model Analyzer (SEC Edgar → LLM → Error)...")
    
    # Initialize components
    yahoo_provider = YahooFinanceProvider()
    llm_manager = LLMManager()
    sec_provider = SECEdgarProvider()
    
    # Create analyzer with SEC provider
    analyzer = BusinessModelAnalyzer(yahoo_provider, llm_manager, sec_provider)
    
    # Test diverse set of companies to test different revenue stream scenarios
    # test_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "TSLA", "JPM", "WMT", "NFLX"]
    # test_tickers = ["LXRX", "LQDT", "EQT", "EVER", "KMDA", "PAVM", "CHRS", "UPWK"]
    test_tickers = ["AAPL", "AMZN"]
    results = {}
    
    for ticker in test_tickers:
        print(f"\n{'='*60}")
        print(f"Analyzing {ticker} - Enhanced Revenue Stream Analysis")
        print(f"{'='*60}")
        
        try:
            # Get financial data
            financial_metrics = yahoo_provider.get_financial_metrics(ticker)
            price_data = yahoo_provider.get_price_data(ticker)
            
            if 'error' in financial_metrics:
                print(f"✗ Failed to get financial data: {financial_metrics['error']}")
                results[ticker] = {'error': financial_metrics['error']}
                continue
                
            # Build analysis_data structure
            analysis_data = {
                'financial_metrics': financial_metrics,
                'price_data': price_data,
                'company_info': {
                    'sector': financial_metrics.get('sector', ''),
                    'industry': financial_metrics.get('industry', ''),
                },
                'company_type': 'mature_profitable',
                'current_price': financial_metrics.get('current_price', 0),
                'quality_grade': 'B'
            }
            
            print(f"✓ Financial data loaded for {ticker}")
            print(f"  Company: {financial_metrics.get('long_name', ticker)}")
            print(f"  Sector: {analysis_data['company_info']['sector']}")
            print(f"  Industry: {analysis_data['company_info']['industry']}")
            print(f"  Revenue: ${financial_metrics.get('total_revenue', 0):,.0f}")
            
            # Run enhanced business model analysis
            print(f"\n--- Enhanced Revenue Stream Analysis ---")
            result = analyzer.analyze(ticker, analysis_data)
            
            if 'error' not in result:
                print(f"✓ Analysis successful for {ticker}")
                print(f"  Business Model: {result.get('business_model_type')}")
                print(f"  Primary Revenue Stream: {result.get('primary_revenue_stream')}")
                print(f"  Recurring Revenue: {(result.get('recurring_percentage') or 0)*100:.1f}%")
                print(f"  Revenue Quality: {result.get('revenue_quality')}")
                print(f"  Scalability Score: {result.get('scalability_score', 0):.1f}/10")
                
                # Store result for JSON output
                results[ticker] = {
                    'success': True,
                    'company_name': financial_metrics.get('long_name', ticker),
                    'analysis_result': result,
                    'financial_summary': {
                        'sector': analysis_data['company_info']['sector'],
                        'industry': analysis_data['company_info']['industry'],
                        'total_revenue': financial_metrics.get('total_revenue', 0),
                        'current_price': analysis_data['current_price']
                    }
                }
                
                # Add SEC Edgar data summary if available
                if 'sec_edgar_data' in result:
                    sec_data = result['sec_edgar_data']
                    print(f"  SEC Edgar Data: {'Available' if sec_data.get('data_available') else 'Not Available'}")
                    if sec_data.get('cik'):
                        print(f"  CIK: {sec_data['cik']}")
                    if sec_data.get('filing_facts'):
                        print(f"  XBRL Fields: {sec_data['filing_facts'].get('total_xbrl_fields', 0)}")
            else:
                print(f"✗ Analysis failed: {result['error']}")
                results[ticker] = {
                    'success': False,
                    'error': result['error'],
                    'company_name': financial_metrics.get('long_name', ticker)
                }
                
        except Exception as e:
            print(f"✗ Error analyzing {ticker}: {e}")
            results[ticker] = {
                'success': False,
                'error': str(e),
                'exception_type': type(e).__name__
            }
    
    # Write results to JSON file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'business_model_analysis_results_{timestamp}.json'
    
    try:
        with open(output_file, 'w') as f:
            json.dump({
                'test_metadata': {
                    'timestamp': timestamp,
                    'test_description': 'Enhanced Business Model Analyzer Test - SEC Edgar → LLM → Error',
                    'tickers_tested': test_tickers,
                    'total_companies': len(test_tickers),
                    'successful_analyses': len([r for r in results.values() if r.get('success')]),
                    'failed_analyses': len([r for r in results.values() if not r.get('success')])
                },
                'results': results
            }, f, indent=2, default=str)
        
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"✓ Results written to: {output_file}")
        print(f"Total companies tested: {len(test_tickers)}")
        print(f"Successful analyses: {len([r for r in results.values() if r.get('success')])}")
        print(f"Failed analyses: {len([r for r in results.values() if not r.get('success')])}")
        
        # Show quick summary of revenue stream analysis results
        print(f"\n--- REVENUE STREAM ANALYSIS SUMMARY ---")
        for ticker, result in results.items():
            if result.get('success'):
                analysis = result['analysis_result']
                print(f"{ticker:6} | {analysis.get('business_model_type', 'N/A'):20} | {analysis.get('primary_revenue_stream', 'N/A'):20} | {(analysis.get('recurring_percentage', 0)*100):5.1f}%")
            else:
                print(f"{ticker:6} | ERROR: {result.get('error', 'Unknown')[:50]}...")
        
    except Exception as e:
        print(f"✗ Failed to write results to file: {e}")

if __name__ == "__main__":
    test_business_model_analyzer()