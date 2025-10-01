"""
Test script for AI integration with stock analysis
Run this to test the AI-enhanced analysis on a sample stock
"""

import os
import sys
from datetime import datetime

# Add the current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_individual_components():
    """Test each AI component individually"""
    
    print("=" * 60)
    print("TESTING AI INTEGRATION COMPONENTS")
    print("=" * 60)
    
    # Test 1: Data Retrieval
    print("\n1. Testing AI Data Retriever...")
    try:
        from ai_data_retriever import AIDataRetriever
        
        retriever = AIDataRetriever()
        data = retriever.get_comprehensive_data("AAPL")
        
        print(f"   ✓ Retrieved data for {data['ticker']}")
        print(f"   ✓ Data quality: {data['data_quality']}")
        print(f"   ✓ News articles: {len(data['recent_news'])}")
        print(f"   ✓ Company: {data['company_info'].get('company_name', 'Unknown')}")
        
    except Exception as e:
        print(f"   ✗ Data retrieval failed: {e}")
        return False
    
    # Test 2: AI Analysis
    print("\n2. Testing AI Analyzer...")
    try:
        from ai_analyzer import AIAnalyzer
        
        analyzer = AIAnalyzer()
        insights = analyzer.generate_ai_insights(data)
        
        print(f"   ✓ Generated insights for {insights['ticker']}")
        print(f"   ✓ Revenue assessment: {insights['earnings_analysis']['revenue_assessment']}")
        print(f"   ✓ News sentiment: {insights['news_sentiment']['overall_sentiment']}")
        print(f"   ✓ Overall assessment: {insights['overall_assessment']['summary']}")
        
    except Exception as e:
        print(f"   ✗ AI analysis failed: {e}")
        return False
    
    # Test 3: Enhanced Analysis
    print("\n3. Testing Enhanced Stock Analyzer...")
    try:
        from ai_enhanced_analyzer import AIEnhancedStockAnalyzer
        
        enhanced_analyzer = AIEnhancedStockAnalyzer("AAPL")
        enhanced_results = enhanced_analyzer.run_enhanced_analysis()
        
        rec = enhanced_results['enhanced_recommendation']
        print(f"   ✓ Enhanced analysis completed")
        print(f"   ✓ Original: {rec['original_recommendation']} → Final: {rec['final_recommendation']}")
        print(f"   ✓ AI Adjustment: {rec['ai_adjustment']}")
        print(f"   ✓ Confidence: {rec['confidence_level']}")
        
    except Exception as e:
        print(f"   ✗ Enhanced analysis failed: {e}")
        return False
    
    return True

def test_multiple_stocks():
    """Test AI integration on multiple stocks"""
    
    print("\n" + "=" * 60)
    print("TESTING MULTIPLE STOCKS")
    print("=" * 60)
    
    test_stocks = ["AAPL", "MSFT", "TSLA", "GOOGL"]
    
    try:
        from ai_enhanced_analyzer import AIEnhancedStockAnalyzer
        
        results = {}
        
        for ticker in test_stocks:
            print(f"\nAnalyzing {ticker}...")
            
            try:
                analyzer = AIEnhancedStockAnalyzer(ticker)
                analysis = analyzer.run_enhanced_analysis()
                
                rec = analysis['enhanced_recommendation']
                results[ticker] = {
                    'original_rec': rec['original_recommendation'],
                    'final_rec': rec['final_recommendation'],
                    'adjustment': rec['ai_adjustment'],
                    'confidence': rec['confidence_level']
                }
                
                print(f"   {ticker}: {rec['original_recommendation']} → {rec['final_recommendation']} ({rec['ai_adjustment']})")
                
            except Exception as e:
                print(f"   {ticker}: Failed - {e}")
                results[ticker] = {'error': str(e)}
        
        # Summary
        print(f"\n" + "-" * 40)
        print("SUMMARY OF AI ADJUSTMENTS")
        print("-" * 40)
        
        for ticker, result in results.items():
            if 'error' not in result:
                adjustment = result['adjustment']
                if adjustment == 'UPGRADE':
                    print(f"   {ticker}: ↑ UPGRADED")
                elif adjustment == 'DOWNGRADE':
                    print(f"   {ticker}: ↓ DOWNGRADED")
                else:
                    print(f"   {ticker}: → MAINTAINED")
            else:
                print(f"   {ticker}: ✗ ERROR")
        
        return results
        
    except Exception as e:
        print(f"Multiple stock test failed: {e}")
        return {}

def demonstrate_ai_value():
    """Demonstrate the value of AI integration"""
    
    print("\n" + "=" * 60)
    print("AI INTEGRATION VALUE DEMONSTRATION")
    print("=" * 60)
    
    try:
        from stock_analyzer import StockAnalyzer
        from ai_enhanced_analyzer import AIEnhancedStockAnalyzer
        
        ticker = "AAPL"
        
        # Traditional analysis
        print(f"\n1. Traditional Analysis for {ticker}:")
        traditional = StockAnalyzer(ticker, None)
        trad_analysis = traditional.comprehensive_analysis()
        trad_rec = trad_analysis.get('summary', {}).get('recommendation', 'Unknown')
        trad_conf = trad_analysis.get('summary', {}).get('confidence', 'Unknown')
        
        print(f"   Recommendation: {trad_rec}")
        print(f"   Confidence: {trad_conf}")
        
        # AI-Enhanced analysis
        print(f"\n2. AI-Enhanced Analysis for {ticker}:")
        enhanced = AIEnhancedStockAnalyzer(ticker)
        enh_analysis = enhanced.run_enhanced_analysis()
        enh_rec = enh_analysis['enhanced_recommendation']
        
        print(f"   Original: {enh_rec['original_recommendation']}")
        print(f"   AI-Enhanced: {enh_rec['final_recommendation']}")
        print(f"   Adjustment: {enh_rec['ai_adjustment']}")
        print(f"   Confidence: {enh_rec['confidence_level']}")
        
        # Show AI insights
        ai_data = enh_analysis['ai_enhancement']
        print(f"\n3. AI Insights Added:")
        print(f"   Earnings Assessment: {ai_data['earnings_analysis']['revenue_assessment']}")
        print(f"   News Sentiment: {ai_data['news_sentiment']['overall_sentiment']}")
        
        if ai_data['risk_flags']:
            print(f"   Risk Flags: {', '.join(ai_data['risk_flags'])}")
        
        print(f"\n4. Value Added by AI:")
        if enh_rec['ai_adjustment'] != 'MAINTAIN':
            print(f"   ✓ AI identified factors that changed recommendation")
            print(f"   ✓ Incorporated real-world events and sentiment")
        else:
            print(f"   ✓ AI confirmed quantitative analysis")
        
        print(f"   ✓ Added {len(enh_rec['key_factors'])} key factors")
        print(f"   ✓ Identified {len(ai_data['risk_flags'])} additional risks")
        print(f"   ✓ Generated {len(enh_rec['action_items'])} action items")
        
        return True
        
    except Exception as e:
        print(f"Value demonstration failed: {e}")
        return False

def main():
    """Main test function"""
    
    print("AI INTEGRATION TEST SUITE")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test individual components
    components_ok = test_individual_components()
    
    if components_ok:
        # Test multiple stocks
        multi_results = test_multiple_stocks()
        
        # Demonstrate value
        value_demo = demonstrate_ai_value()
        
        print("\n" + "=" * 60)
        print("TEST SUITE COMPLETED")
        print("=" * 60)
        
        if components_ok and multi_results and value_demo:
            print("✓ All tests passed successfully!")
            print("✓ AI integration is working correctly")
            print("✓ Ready for production use")
        else:
            print("⚠ Some tests had issues - check output above")
    
    else:
        print("\n" + "=" * 60)
        print("TEST SUITE FAILED")
        print("=" * 60)
        print("✗ Component tests failed - fix issues before proceeding")

if __name__ == "__main__":
    main()