#!/usr/bin/env python3
"""
Load existing analysis results into the database
"""

import pandas as pd
import json
import sys
import os
from datetime import datetime
import glob

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.share_insights_v1.services.database.analysis_database import AnalysisDatabase

def load_csv_to_database():
    """Load analysis results from CSV files into database"""
    
    db = AnalysisDatabase()
    
    # Find all analysis CSV files
    analysis_files = glob.glob("src/share_insights_v1/resources/stock_analyses/*_analysis.csv")
    
    if not analysis_files:
        print("No analysis CSV files found")
        return
    
    total_loaded = 0
    
    for file_path in analysis_files:
        print(f"Processing {file_path}...")
        
        try:
            # Extract batch info from filename
            filename = os.path.basename(file_path)
            parts = filename.replace('_analysis.csv', '').split('_')
            exchange = parts[0].upper()
            batch_date = parts[1] if len(parts) > 1 else datetime.now().strftime('%Y%m%d')
            batch_id = f"{exchange}_{batch_date}"
            
            # Read CSV
            df = pd.read_csv(file_path)
            
            if df.empty:
                print(f"  Empty file: {filename}")
                continue
            
            loaded_count = 0
            
            for _, row in df.iterrows():
                try:
                    # Create analysis result structure
                    analysis_result = {
                        'ticker': row.get('ticker', ''),
                        'company_type': row.get('company_type', ''),
                        'quality_score': {'grade': row.get('quality_grade', 'C')},
                        'final_recommendation': create_recommendation_object(row),
                        'analyses': extract_method_analyses(row),
                        'execution_time_seconds': row.get('execution_time_seconds', 0),
                        'analyses_count': row.get('analyses_count', 0)
                    }
                    
                    # Store in database
                    if db.store_analysis_result(analysis_result, batch_id):
                        loaded_count += 1
                    
                except Exception as e:
                    print(f"  Error processing row for {row.get('ticker', 'unknown')}: {e}")
                    continue
            
            print(f"  Loaded {loaded_count}/{len(df)} records from {filename}")
            total_loaded += loaded_count
            
        except Exception as e:
            print(f"  Error processing file {filename}: {e}")
            continue
    
    print(f"\nTotal records loaded: {total_loaded}")
    
    # Show summary
    summary = db.get_analysis_summary()
    print(f"Database now contains {summary['total_stocks']} unique stocks")
    print(f"Exchange distribution: {summary['exchange_distribution']}")
    print(f"Recommendation distribution: {summary['recommendation_distribution']}")

def create_recommendation_object(row):
    """Create recommendation object from CSV row"""
    class MockRecommendation:
        def __init__(self, rec, target, confidence, upside, risk):
            self.recommendation = rec
            self.target_price = target
            self.confidence = confidence
            self.upside_potential = upside
            self.risk_level = risk
    
    return MockRecommendation(
        rec=row.get('final_recommendation', 'Hold'),
        target=float(row.get('target_price', 0)) if pd.notna(row.get('target_price')) else 0,
        confidence=row.get('confidence', 'Medium'),
        upside=float(row.get('upside_potential', 0)) if pd.notna(row.get('upside_potential')) else 0,
        risk=row.get('risk_level', 'Medium')
    )

def extract_method_analyses(row):
    """Extract individual method analyses from CSV row"""
    analyses = {}
    
    # Map CSV columns to analysis methods
    method_mapping = {
        'dcf_recommendation': 'dcf',
        'technical_recommendation': 'technical', 
        'comparable_recommendation': 'comparable',
        'ai_insights_recommendation': 'ai_insights',
        'news_sentiment_recommendation': 'news_sentiment',
        'business_model_recommendation': 'business_model',
        'competitive_position_recommendation': 'competitive_position',
        'management_quality_recommendation': 'management_quality',
        'analyst_consensus_recommendation': 'analyst_consensus',
        'industry_analysis_recommendation': 'industry_analysis'
    }
    
    for csv_col, method_name in method_mapping.items():
        if csv_col in row and pd.notna(row[csv_col]):
            analyses[method_name] = {
                'recommendation': row[csv_col],
                'confidence': 'Medium'  # Default since not in CSV
            }
    
    return analyses

if __name__ == "__main__":
    print("Loading analysis results into database...")
    load_csv_to_database()
    print("Done!")