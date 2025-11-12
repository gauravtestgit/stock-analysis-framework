#!/usr/bin/env python3
"""Test new DCF architecture with MU case"""

import os
import json
import yfinance as yf
from ..implementations.calculators.dcf_yf_new import get_share_price
from ..config.config import FinanceConfig
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider

def test_new_dcf_architecture():
    """Test new DCF architecture with proper company classification"""
    
    ticker = "chrs"
    yp = YahooFinanceProvider()
    
    # Get comprehensive data like DCF analyzer does
    metrics = yp.get_financial_metrics(ticker=ticker)
    sector = metrics.get('sector', '')
    industry = metrics.get('industry', '')
    
    print(f"Testing new DCF architecture for {ticker.upper()}")
    print(f"Sector: {sector}, Industry: {industry}")
    print("=" * 50)
    
    try:
        # Determine company type and quality like DCF analyzer
        from ..implementations.calculators.quality_calculator import QualityScoreCalculator
        from ..implementations.classifier import CompanyClassifier
        
        # Get quality assessment
        qs = QualityScoreCalculator()
        quality = qs.calculate(metrics=metrics)
        quality_grade = quality.get('grade', 'C')
        
        # Debug quality calculation
        print(f"Quality Details:")
        print(f"  Score: {quality.get('quality_score', 0)}/100")
        print(f"  Missing Penalty: {quality.get('missing_penalty', 0)}")
        print(f"  Data Quality: {quality.get('data_quality', 'Unknown')}")
        print(f"  Key Metrics:")
        print(f"    ROE: {metrics.get('roe', 'N/A')}")
        print(f"    Debt/Equity: {metrics.get('debt_to_equity', 'N/A')}")
        print(f"    Revenue Growth: {metrics.get('yearly_revenue_growth', 'N/A')}")
        print(f"    P/E Ratio: {metrics.get('pe_ratio', 'N/A')}")
        print()
        
        # Classify company type
        company_classifier = CompanyClassifier()
        company_type = company_classifier.classify(ticker=ticker, metrics=metrics)
        
        print(f"Company Type: {company_type}")
        print(f"Quality Grade: {quality_grade}")
        print()
        
        # Get adjusted parameters and create config like DCF analyzer does
        config = FinanceConfig()
        params = config.get_adjusted_parameters(
            sector=sector,
            industry=industry,
            company_type=company_type,
            quality_grade=quality_grade
        )
        
        # Create temporary config with adjusted parameters
        tmp_config = FinanceConfig()
        tmp_config.use_default_ebitda_multiple = True
        tmp_config.default_ev_ebitda_multiple = params.get('ev_ebitda_multiple', tmp_config.default_ev_ebitda_multiple)
        tmp_config.max_cagr_threshold = params.get('max_cagr', tmp_config.max_cagr_threshold)
        tmp_config.default_terminal_growth = params.get('terminal_growth', tmp_config.default_terminal_growth)
        
        # Pass company type for risk adjustments (like DCF analyzer does)
        tmp_config.company_type = company_type
        
        # Use new architecture with clean interface
        result = get_share_price(ticker, tmp_config)
        
        print("✅ New DCF Architecture Results:")
        print(f"Share Price: ${result['share_price']:.2f}")
        print(f"Current Price: ${result['last_close_price']:.2f}")
        print(f"FCF CAGR: {result['fcf_cagr']:.1%}")
        print(f"EBITDA CAGR: {result['ebitda_cagr']:.1%}")
        print(f"Terminal Ratio: {result['terminal_ratio']:.1%}")
        print(f"Confidence: {result['confidence']}")
        
        if 'terminal_adjustment_factor' in result:
            print(f"Terminal Adjustment: {result['terminal_adjustment_factor']:.2f}x")
        
        # Calculate upside/downside
        upside = ((result['share_price'] - result['last_close_price']) / result['last_close_price']) * 100
        print(f"Upside/Downside: {upside:+.1f}%")
        
        print("\n📊 Key Improvements:")
        if result['terminal_ratio'] < 0.90:
            print("✅ Terminal value dominance controlled")
        if result['confidence'] in ['Medium', 'High']:
            print("✅ Appropriate confidence level")
        if abs(upside) < 50:
            print("✅ Reasonable valuation range")
        
        print(f"\n🔧 Full Results:")
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_comparison_with_stable_company():
    """Test with a stable company for comparison"""
    
    ticker = "tsla"
    yp = YahooFinanceProvider()
    
    # Get comprehensive data
    metrics = yp.get_financial_metrics(ticker=ticker)
    sector = metrics.get('sector', '')
    industry = metrics.get('industry', '')
    
    print(f"\n\nTesting stable company: {ticker}")
    print(f"Sector: {sector}, Industry: {industry}")
    print("=" * 50)
    
    try:
        # Determine company type and quality
        from ..implementations.calculators.quality_calculator import QualityScoreCalculator
        from ..implementations.classifier import CompanyClassifier
        
        qs = QualityScoreCalculator()
        quality = qs.calculate(metrics=metrics)
        quality_grade = quality.get('grade', 'C')
        
        company_classifier = CompanyClassifier()
        company_type = company_classifier.classify(ticker=ticker, metrics=metrics)
        
        print(f"Company Type: {company_type}")
        print(f"Quality Grade: {quality_grade}")
        print()
        
        # Get adjusted parameters like DCF analyzer
        config = FinanceConfig()
        params = config.get_adjusted_parameters(
            sector=sector,
            industry=industry,
            company_type=company_type,
            quality_grade=quality_grade
        )
        
        tmp_config = FinanceConfig()
        tmp_config.use_default_ebitda_multiple = True
        tmp_config.default_ev_ebitda_multiple = params.get('ev_ebitda_multiple', tmp_config.default_ev_ebitda_multiple)
        tmp_config.max_cagr_threshold = params.get('max_cagr', tmp_config.max_cagr_threshold)
        tmp_config.default_terminal_growth = params.get('terminal_growth', tmp_config.default_terminal_growth)
        
        # Pass company type for risk adjustments
        tmp_config.company_type = company_type
        
        result = get_share_price(ticker, tmp_config)
        
        print("✅ Stable Company Results:")
        print(f"Share Price: ${result['share_price']:.2f}")
        print(f"Current Price: ${result['last_close_price']:.2f}")
        print(f"Terminal Ratio: {result['terminal_ratio']:.1%}")
        print(f"Confidence: {result['confidence']}")
        
        upside = ((result['share_price'] - result['last_close_price']) / result['last_close_price']) * 100
        print(f"Upside/Downside: {upside:+.1f}%")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    os.environ['DEBUG'] = 'true'
    test_new_dcf_architecture()
    # test_comparison_with_stable_company()