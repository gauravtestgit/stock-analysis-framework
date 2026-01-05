from typing import Optional, Dict, Any, List
from datetime import datetime
from ...models.database import SessionLocal
from ...models.strategy_models import InvestmentThesis, AnalysisHistory

class ThesisStorageService:
    """Service for storing and retrieving investment theses"""
    
    def store_thesis(self, ticker: str, thesis_type: str, content: str, 
                    llm_provider: str = None, llm_model: str = None,
                    prompt_template: str = None, batch_analysis_id: str = None,
                    previous_thesis_id: int = None) -> Optional[int]:
        """Store investment thesis and return thesis ID"""
        db = SessionLocal()
        try:
            thesis = InvestmentThesis(
                ticker=ticker,
                thesis_type=thesis_type,
                content=content,
                llm_provider=llm_provider,
                llm_model=llm_model,
                prompt_template=prompt_template,
                batch_analysis_id=batch_analysis_id,
                previous_thesis_id=previous_thesis_id
            )
            db.add(thesis)
            db.commit()
            db.refresh(thesis)
            return thesis.id
        except Exception as e:
            db.rollback()
            print(f"Failed to store thesis for {ticker}: {e}")
            return None
        finally:
            db.close()
    
    def get_thesis_history(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get thesis history for a ticker"""
        db = SessionLocal()
        try:
            theses = db.query(InvestmentThesis)\
                      .filter(InvestmentThesis.ticker == ticker)\
                      .order_by(InvestmentThesis.created_at.desc())\
                      .limit(limit)\
                      .all()
            
            return [{
                'id': thesis.id,
                'thesis_type': thesis.thesis_type,
                'content': thesis.content,
                'llm_provider': thesis.llm_provider,
                'llm_model': thesis.llm_model,
                'created_at': thesis.created_at,
                'previous_thesis_id': thesis.previous_thesis_id
            } for thesis in theses]
        except Exception as e:
            print(f"Failed to get thesis history for {ticker}: {e}")
            return []
        finally:
            db.close()
    
    def get_latest_thesis(self, ticker: str, thesis_type: str = None) -> Optional[Dict[str, Any]]:
        """Get latest thesis for ticker and optional type"""
        db = SessionLocal()
        try:
            query = db.query(InvestmentThesis).filter(InvestmentThesis.ticker == ticker)
            if thesis_type:
                query = query.filter(InvestmentThesis.thesis_type == thesis_type)
            
            thesis = query.order_by(InvestmentThesis.created_at.desc()).first()
            
            if thesis:
                return {
                    'id': thesis.id,
                    'thesis_type': thesis.thesis_type,
                    'content': thesis.content,
                    'llm_provider': thesis.llm_provider,
                    'llm_model': thesis.llm_model,
                    'created_at': thesis.created_at
                }
            return None
        except Exception as e:
            print(f"Failed to get latest thesis for {ticker}: {e}")
            return None
        finally:
            db.close()