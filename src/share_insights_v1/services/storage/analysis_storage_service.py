from typing import Optional, Dict, Any
from ..database.database_service import DatabaseService
from ...models.database import SessionLocal

class AnalysisStorageService:
    """Service for storing analysis results independently"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    def store_comprehensive_analysis(self, ticker: str, analysis_results: Dict[str, Any], 
                                   scenario_context_id: Optional[int] = None) -> str:
        """Store comprehensive analysis results from orchestrator and return batch_analysis_id"""
        import uuid
        
        # Generate unique batch analysis ID as UUID object
        batch_analysis_id = uuid.uuid4()
        
        db = SessionLocal()
        try:
            self.db_service.save_comprehensive_analysis(
                db, ticker, analysis_results, scenario_context_id, batch_analysis_id
            )
            return str(batch_analysis_id)
        except Exception as e:
            print(f"Failed to store analysis for {ticker}: {e}")
            raise e
        finally:
            db.close()
    
    def store_single_analysis(self, ticker: str, analysis_type: str, 
                            recommendation: str, target_price: float,
                            confidence: str, raw_data: Dict[str, Any],
                            scenario_context_id: Optional[int] = None) -> bool:
        """Store individual analyzer result"""
        db = SessionLocal()
        try:
            self.db_service.save_analysis_result(
                db, ticker, analysis_type, recommendation, 
                target_price, confidence, raw_data, scenario_context_id
            )
            return True
        except Exception as e:
            print(f"Failed to store {analysis_type} analysis for {ticker}: {e}")
            return False
        finally:
            db.close()
    
    def get_latest_analysis(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Retrieve latest analysis for a ticker"""
        db = SessionLocal()
        try:
            return self.db_service.get_latest_analysis(db, ticker)
        except Exception as e:
            print(f"Failed to retrieve analysis for {ticker}: {e}")
            return None
        finally:
            db.close()