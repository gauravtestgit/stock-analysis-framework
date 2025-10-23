#!/usr/bin/env python3

import sys
import os

from ..models.database import SessionLocal
from ..services.database.database_service import DatabaseService

def test_comprehensive_analysis_storage():
    """Test storing comprehensive analysis results from multiple analyzers"""
    
    db_service = DatabaseService()
    db = SessionLocal()
    
    try:
        print("=== Testing Comprehensive Analysis Storage ===")
        
        # Mock comprehensive analysis result (like from orchestrator)
        comprehensive_analysis = {
            'ticker': 'AAPL',
            'company_type': 'established',
            'analyses_count': 5,
            'execution_time_seconds': 12.5,
            'final_recommendation': {
                'recommendation': 'Buy',
                'target_price': 185.0,
                'confidence': 'High',
                'consensus_score': 0.75
            },
            'analyses': {
                'dcf': {
                    'method': 'DCF Analysis',
                    'recommendation': 'Strong Buy',
                    'predicted_price': 190.0,
                    'confidence': 'High',
                    'parameters_used': {
                        'discount_rate': 0.10,
                        'terminal_growth': 0.03,
                        'fcf_growth': 0.08
                    }
                },
                'technical': {
                    'method': 'Technical Analysis',
                    'recommendation': 'Buy',
                    'predicted_price': 175.0,
                    'confidence': 'Medium',
                    'trend': 'Uptrend',
                    'rsi_14': 65.2,
                    'ma_20': 168.5,
                    'ma_50': 162.3
                },
                'ai_insights': {
                    'method': 'AI Insights Analysis',
                    'recommendation': 'Buy',
                    'predicted_price': 180.0,
                    'confidence': 'High',
                    'ai_insights': {
                        'market_position': 'Strong',
                        'growth_prospects': 'High',
                        'competitive_advantage': 'Strong'
                    }
                },
                'news_sentiment': {
                    'method': 'News Sentiment Analysis',
                    'recommendation': 'Hold',
                    'predicted_price': 170.0,
                    'confidence': 'Medium',
                    'overall_sentiment_score': 0.65,
                    'news_count': 15,
                    'sentiment_rating': 'Positive'
                },
                'financial_health': {
                    'method': 'Financial Health Analysis',
                    'recommendation': 'Buy',
                    'predicted_price': 182.0,
                    'confidence': 'High',
                    'overall_grade': 'A',
                    'cash_flow_score': 'Excellent',
                    'debt_score': 'Good'
                }
            }
        }
        
        print("\\n1. Saving comprehensive analysis...")
        saved_analyses = db_service.save_comprehensive_analysis(
            db=db,
            ticker='AAPL',
            analysis_results=comprehensive_analysis
        )
        print(f"Saved {len(saved_analyses)} analysis records")
        
        print("\\n2. Retrieving latest analysis...")
        latest_analysis = db_service.get_latest_analysis(db, 'AAPL')
        if latest_analysis:
            print(f"Retrieved analysis for {latest_analysis['ticker']}")
            print(f"Final recommendation: {latest_analysis['final_recommendation']['recommendation']}")
            print(f"Target price: ${latest_analysis['final_recommendation']['target_price']:.2f}")
            print(f"Individual analyses: {len(latest_analysis['analyses'])}")
            
            for analysis_type, data in latest_analysis['analyses'].items():
                print(f"  - {analysis_type}: {data['recommendation']} (${data.get('predicted_price', 0):.2f})")
        
        print("\\n3. Testing analysis history...")
        history = db_service.get_analysis_history(db, 'AAPL', limit=20)
        print(f"Total analysis records: {len(history)}")
        
        # Group by type
        by_type = {}
        for record in history:
            if record.analysis_type not in by_type:
                by_type[record.analysis_type] = 0
            by_type[record.analysis_type] += 1
        
        print("Records by type:")
        for analysis_type, count in by_type.items():
            print(f"  - {analysis_type}: {count}")
        
        print("\\n4. Testing analysis comparison...")
        comparison = db_service.get_analysis_comparison(db, 'AAPL', days_back=7)
        print(f"Analysis comparison for {comparison['ticker']} (last {comparison['period_days']} days):")
        print(f"Total analyses: {comparison['total_analyses']}")
        
        for analysis_type, records in comparison['by_type'].items():
            print(f"  - {analysis_type}: {len(records)} records")
            if records:
                latest_rec = records[0]  # Most recent
                print(f"    Latest: {latest_rec['recommendation']} (${latest_rec['target_price']:.2f})")
        
        print("\\n5. Testing multiple analysis runs...")
        # Simulate running analysis again with different results
        updated_analysis = comprehensive_analysis.copy()
        updated_analysis['final_recommendation']['target_price'] = 188.0
        updated_analysis['analyses']['dcf']['predicted_price'] = 195.0
        
        saved_analyses_2 = db_service.save_comprehensive_analysis(
            db=db,
            ticker='AAPL',
            analysis_results=updated_analysis
        )
        print(f"Saved second analysis run: {len(saved_analyses_2)} records")
        
        # Check history again
        updated_history = db_service.get_analysis_history(db, 'AAPL', limit=20)
        print(f"Updated total analysis records: {len(updated_history)}")
        
        print("\\n✅ Comprehensive analysis storage test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during analysis storage test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_comprehensive_analysis_storage()