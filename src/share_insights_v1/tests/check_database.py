#!/usr/bin/env python3
"""
Check what's in the analysis database
"""

import sqlite3
import pandas as pd
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.share_insights_v1.services.database.analysis_database import AnalysisDatabase

def check_database():
    """Check database contents"""
    
    db_path = "finance_analysis.db"
    
    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist")
        return
    
    print(f"Database file: {db_path}")
    print(f"File size: {os.path.getsize(db_path)} bytes")
    
    # Connect directly to check tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"\\nTables in database: {[t[0] for t in tables]}")
    
    # Check analysis_history table
    if ('analysis_history',) in tables:
        cursor.execute("SELECT COUNT(*) FROM analysis_history")
        total_rows = cursor.fetchone()[0]
        print(f"\\nTotal rows in analysis_history: {total_rows}")
        
        if total_rows > 0:
            # Show sample data
            cursor.execute("SELECT ticker, analysis_date, final_recommendation, exchange FROM analysis_history LIMIT 5")
            sample_data = cursor.fetchall()
            print("\\nSample data:")
            for row in sample_data:
                print(f"  {row}")
            
            # Show column info
            cursor.execute("PRAGMA table_info(analysis_history)")
            columns = cursor.fetchall()
            print(f"\\nColumns in analysis_history: {len(columns)}")
            for col in columns[:10]:  # Show first 10 columns
                print(f"  {col[1]} ({col[2]})")
            
            # Check for NULL values in key fields
            cursor.execute("SELECT COUNT(*) FROM analysis_history WHERE final_recommendation IS NULL OR final_recommendation = ''")
            null_recommendations = cursor.fetchone()[0]
            print(f"\\nRows with NULL/empty final_recommendation: {null_recommendations}")
            
            cursor.execute("SELECT COUNT(*) FROM analysis_history WHERE exchange IS NULL OR exchange = ''")
            null_exchange = cursor.fetchone()[0]
            print(f"Rows with NULL/empty exchange: {null_exchange}")
            
            # Show unique values
            cursor.execute("SELECT DISTINCT final_recommendation FROM analysis_history WHERE final_recommendation IS NOT NULL AND final_recommendation != ''")
            recommendations = [r[0] for r in cursor.fetchall()]
            print(f"\\nUnique recommendations: {recommendations}")
            
            cursor.execute("SELECT DISTINCT exchange FROM analysis_history WHERE exchange IS NOT NULL AND exchange != ''")
            exchanges = [e[0] for e in cursor.fetchall()]
            print(f"Unique exchanges: {exchanges}")
    
    conn.close()
    
    # Test the AnalysisDatabase class
    print("\\n" + "="*50)
    print("Testing AnalysisDatabase class:")
    
    db = AnalysisDatabase(db_path)
    
    # Test get_analysis_summary
    summary = db.get_analysis_summary()
    print(f"\\nSummary from AnalysisDatabase:")
    print(f"  Total stocks: {summary.get('total_stocks', 0)}")
    print(f"  Exchange distribution: {summary.get('exchange_distribution', {})}")
    print(f"  Recommendation distribution: {summary.get('recommendation_distribution', {})}")
    
    # Test search_stocks with no filters
    df = db.search_stocks(limit=10)
    print(f"\\nSearch results (no filters): {len(df)} rows")
    if not df.empty:
        print("Sample results:")
        print(df[['ticker', 'final_recommendation', 'exchange']].head())

if __name__ == "__main__":
    check_database()