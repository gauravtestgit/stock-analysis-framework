import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

class AnalysisDatabase:
    """Database service for storing and retrieving stock analysis results"""
    
    def __init__(self, db_path="finance_analysis.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create analysis_history table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker VARCHAR(20) NOT NULL,
            analysis_date TIMESTAMP NOT NULL,
            batch_id VARCHAR(50),
            exchange VARCHAR(10),
            company_type VARCHAR(30),
            quality_grade VARCHAR(5),
            final_recommendation VARCHAR(20),
            target_price DECIMAL(10,2),
            confidence VARCHAR(10),
            upside_potential DECIMAL(8,2),
            risk_level VARCHAR(10),
            dcf_recommendation VARCHAR(20),
            technical_recommendation VARCHAR(20),
            comparable_recommendation VARCHAR(20),
            ai_insights_recommendation VARCHAR(20),
            news_sentiment_recommendation VARCHAR(20),
            business_model_recommendation VARCHAR(20),
            competitive_position_recommendation VARCHAR(20),
            management_quality_recommendation VARCHAR(20),
            analyst_consensus_recommendation VARCHAR(20),
            industry_analysis_recommendation VARCHAR(20),
            analysis_data TEXT,
            execution_time_seconds DECIMAL(8,2),
            analyses_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create index for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker_date ON analysis_history(ticker, analysis_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exchange ON analysis_history(exchange)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendation ON analysis_history(final_recommendation)")
        
        conn.commit()
        conn.close()
    
    def store_analysis_result(self, analysis_result: Dict[str, Any], batch_id: str = None) -> bool:
        """Store a single analysis result in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract data from analysis result
            ticker = analysis_result.get('ticker', '')
            
            # Determine exchange from ticker
            exchange = self._determine_exchange(ticker)
            
            # Extract final recommendation
            final_rec = analysis_result.get('final_recommendation')
            if hasattr(final_rec, 'recommendation'):
                recommendation = final_rec.recommendation.value if hasattr(final_rec.recommendation, 'value') else str(final_rec.recommendation)
                target_price = getattr(final_rec, 'target_price', 0)
                confidence = getattr(final_rec, 'confidence', 'Medium')
                upside_potential = getattr(final_rec, 'upside_potential', 0)
            else:
                recommendation = 'Hold'
                target_price = 0
                confidence = 'Low'
                upside_potential = 0
            
            # Extract individual method recommendations
            analyses = analysis_result.get('analyses', {})
            
            # Insert data
            cursor.execute("""
            INSERT INTO analysis_history (
                ticker, analysis_date, batch_id, exchange, company_type, quality_grade,
                final_recommendation, target_price, confidence, upside_potential, risk_level,
                dcf_recommendation, technical_recommendation, comparable_recommendation,
                ai_insights_recommendation, news_sentiment_recommendation, business_model_recommendation,
                competitive_position_recommendation, management_quality_recommendation,
                analyst_consensus_recommendation, industry_analysis_recommendation,
                analysis_data, execution_time_seconds, analyses_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                datetime.now().isoformat(),
                batch_id,
                exchange,
                analysis_result.get('company_type', ''),
                analysis_result.get('quality_score', {}).get('grade', 'C'),
                recommendation,
                float(target_price) if target_price else 0,
                confidence,
                float(upside_potential) if upside_potential else 0,
                getattr(final_rec, 'risk_level', 'Medium') if final_rec else 'Medium',
                analyses.get('dcf', {}).get('recommendation', ''),
                analyses.get('technical', {}).get('recommendation', ''),
                analyses.get('comparable', {}).get('recommendation', ''),
                analyses.get('ai_insights', {}).get('recommendation', ''),
                analyses.get('news_sentiment', {}).get('recommendation', ''),
                analyses.get('business_model', {}).get('recommendation', ''),
                analyses.get('competitive_position', {}).get('recommendation', ''),
                analyses.get('management_quality', {}).get('recommendation', ''),
                analyses.get('analyst_consensus', {}).get('recommendation', ''),
                analyses.get('industry_analysis', {}).get('recommendation', ''),
                json.dumps(analysis_result, default=str),
                analysis_result.get('execution_time_seconds', 0),
                analysis_result.get('analyses_count', 0)
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error storing analysis result for {ticker}: {e}")
            return False
    
    def store_batch_results(self, batch_results: Dict[str, Any], batch_id: str = None) -> int:
        """Store multiple analysis results from batch processing"""
        if not batch_id:
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        stored_count = 0
        
        for ticker, result in batch_results.items():
            if isinstance(result, dict) and 'error' not in result:
                if self.store_analysis_result(result, batch_id):
                    stored_count += 1
        
        return stored_count
    
    def get_latest_analysis(self, exchange: str = None, limit: int = None) -> pd.DataFrame:
        """Get latest analysis for each ticker, optionally filtered by exchange"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        WITH latest_analysis AS (
            SELECT ticker, MAX(analysis_date) as latest_date
            FROM analysis_history
            GROUP BY ticker
        )
        SELECT ah.* 
        FROM analysis_history ah
        INNER JOIN latest_analysis la ON ah.ticker = la.ticker AND ah.analysis_date = la.latest_date
        """
        
        params = []
        if exchange:
            query += " WHERE ah.exchange = ?"
            params.append(exchange)
        
        query += " ORDER BY ah.analysis_date DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    def get_ticker_history(self, ticker: str) -> pd.DataFrame:
        """Get all historical analysis for a specific ticker"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT * FROM analysis_history 
        WHERE ticker = ?
        ORDER BY analysis_date DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(ticker,))
        conn.close()
        return df
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary statistics of stored analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total stocks analyzed
        cursor.execute("SELECT COUNT(DISTINCT ticker) FROM analysis_history")
        total_stocks = cursor.fetchone()[0]
        
        # Latest batch info
        cursor.execute("""
        SELECT batch_id, COUNT(*) as count, MAX(analysis_date) as latest_date
        FROM analysis_history 
        WHERE batch_id IS NOT NULL
        GROUP BY batch_id
        ORDER BY latest_date DESC
        LIMIT 1
        """)
        latest_batch = cursor.fetchone()
        
        # Recommendation distribution
        cursor.execute("""
        WITH latest_analysis AS (
            SELECT ticker, MAX(analysis_date) as latest_date
            FROM analysis_history
            GROUP BY ticker
        )
        SELECT ah.final_recommendation, COUNT(*) as count
        FROM analysis_history ah
        INNER JOIN latest_analysis la ON ah.ticker = la.ticker AND ah.analysis_date = la.latest_date
        GROUP BY ah.final_recommendation
        """)
        rec_distribution = dict(cursor.fetchall())
        
        # Exchange distribution
        cursor.execute("""
        WITH latest_analysis AS (
            SELECT ticker, MAX(analysis_date) as latest_date
            FROM analysis_history
            GROUP BY ticker
        )
        SELECT ah.exchange, COUNT(*) as count
        FROM analysis_history ah
        INNER JOIN latest_analysis la ON ah.ticker = la.ticker AND ah.analysis_date = la.latest_date
        GROUP BY ah.exchange
        """)
        exchange_distribution = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_stocks': total_stocks,
            'latest_batch': {
                'batch_id': latest_batch[0] if latest_batch else None,
                'count': latest_batch[1] if latest_batch else 0,
                'date': latest_batch[2] if latest_batch else None
            },
            'recommendation_distribution': rec_distribution,
            'exchange_distribution': exchange_distribution
        }
    
    def _determine_exchange(self, ticker: str) -> str:
        """Determine exchange based on ticker format"""
        if ticker.endswith('.ax'):
            return 'ASX'
        elif ticker.endswith('.nz'):
            return 'NZX'
        elif len(ticker) <= 4 and ticker.isupper():
            return 'NASDAQ'
        else:
            return 'NYSE'
    
    def search_stocks(self, 
                     recommendation: str = None,
                     exchange: str = None,
                     quality_grade: str = None,
                     min_upside: float = None,
                     limit: int = 100) -> pd.DataFrame:
        """Search stocks with various filters"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        WITH latest_analysis AS (
            SELECT ticker, MAX(analysis_date) as latest_date
            FROM analysis_history
            GROUP BY ticker
        )
        SELECT ah.* 
        FROM analysis_history ah
        INNER JOIN latest_analysis la ON ah.ticker = la.ticker AND ah.analysis_date = la.latest_date
        WHERE 1=1
        """
        
        params = []
        
        if recommendation:
            query += " AND ah.final_recommendation = ?"
            params.append(recommendation)
        
        if exchange:
            query += " AND ah.exchange = ?"
            params.append(exchange)
        
        if quality_grade:
            query += " AND ah.quality_grade = ?"
            params.append(quality_grade)
        
        if min_upside is not None:
            query += " AND ah.upside_potential >= ?"
            params.append(min_upside)
        
        query += " ORDER BY ah.upside_potential DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df