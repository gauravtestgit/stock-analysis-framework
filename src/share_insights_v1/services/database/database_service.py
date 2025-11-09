from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from ...models.database import get_db, create_tables
from ...models.strategy_models import (
    Scenario, ScenarioOutcome, Strategy, StrategyScenario, 
    Portfolio, Position, AnalysisHistory, NewsEvent
)

class DatabaseService:
    """Service for database operations"""
    
    def __init__(self):
        create_tables()
    
    def create_scenario(self, db: Session, name: str, description: str, 
                       category: str, base_probability: float = 0.5,
                       timeframe: str = "6M") -> Scenario:
        """Create a new scenario"""
        scenario = Scenario(
            name=name,
            description=description,
            category=category,
            base_probability=base_probability,
            current_probability=base_probability,
            timeframe=timeframe
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        return scenario
    
    def create_scenario_outcomes(self, db: Session, scenario_id: int, 
                                outcomes: List[dict]) -> List[ScenarioOutcome]:
        """Create outcomes for a scenario"""
        outcome_objects = []
        for outcome_data in outcomes:
            outcome = ScenarioOutcome(
                scenario_id=scenario_id,
                name=outcome_data['name'],
                probability=outcome_data['probability'],
                impact_description=outcome_data.get('impact_description', ''),
                expected_duration=outcome_data.get('expected_duration', '3M')
            )
            db.add(outcome)
            outcome_objects.append(outcome)
        
        db.commit()
        return outcome_objects
    
    def create_strategy(self, db: Session, name: str, description: str,
                       strategy_type: str = "scenario_based",
                       timeframe: str = "6M",
                       risk_tolerance: str = "moderate") -> Strategy:
        """Create a new investment strategy"""
        strategy = Strategy(
            name=name,
            description=description,
            strategy_type=strategy_type,
            timeframe=timeframe,
            risk_tolerance=risk_tolerance
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        return strategy
    
    def link_strategy_scenario(self, db: Session, strategy_id: int, 
                              scenario_id: int, weight: float = 1.0,
                              impact_factor: float = 1.0) -> StrategyScenario:
        """Link a strategy to a scenario"""
        link = StrategyScenario(
            strategy_id=strategy_id,
            scenario_id=scenario_id,
            weight=weight,
            impact_factor=impact_factor
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link
    
    def create_portfolio(self, db: Session, strategy_id: int, name: str,
                        initial_value: float = 100000.0) -> Portfolio:
        """Create a portfolio for a strategy"""
        portfolio = Portfolio(
            strategy_id=strategy_id,
            name=name,
            total_value=initial_value,
            cash_balance=initial_value
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
        return portfolio
    
    def add_position(self, db: Session, portfolio_id: int, ticker: str,
                    target_weight: float, scenario_adjustment: float = 1.0) -> Position:
        """Add a position to a portfolio"""
        position = Position(
            portfolio_id=portfolio_id,
            ticker=ticker,
            target_weight=target_weight,
            scenario_adjustment=scenario_adjustment
        )
        db.add(position)
        db.commit()
        db.refresh(position)
        return position
    
    def save_analysis_result(self, db: Session, ticker: str, analysis_type: str,
                           recommendation: str, target_price: float,
                           confidence: str, raw_data: dict,
                           scenario_context_id: Optional[int] = None) -> AnalysisHistory:
        """Save analysis result to history"""
        analysis = AnalysisHistory(
            ticker=ticker,
            analysis_type=analysis_type,
            recommendation=recommendation,
            target_price=target_price,
            confidence=confidence,
            raw_data=raw_data,
            scenario_context_id=scenario_context_id
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
    
    def update_scenario_probability(self, db: Session, scenario_id: int,
                                   new_probability: float, reason: str = "") -> Scenario:
        """Update scenario probability"""
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if scenario:
            scenario.current_probability = new_probability
            scenario.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(scenario)
        return scenario
    
    def get_active_scenarios(self, db: Session) -> List[Scenario]:
        """Get all active scenarios"""
        return db.query(Scenario).filter(Scenario.status == "active").all()
    
    def get_strategy_scenarios(self, db: Session, strategy_id: int) -> List[StrategyScenario]:
        """Get scenarios linked to a strategy"""
        return db.query(StrategyScenario).filter(
            StrategyScenario.strategy_id == strategy_id
        ).all()
    
    def get_portfolio_positions(self, db: Session, portfolio_id: int) -> List[Position]:
        """Get all positions in a portfolio"""
        return db.query(Position).filter(Position.portfolio_id == portfolio_id).all()
    
    def save_comprehensive_analysis(self, db: Session, ticker: str, 
                                   analysis_results: dict, 
                                   scenario_context_id: Optional[int] = None) -> List[AnalysisHistory]:
        """Save comprehensive analysis results from multiple analyzers"""
        saved_analyses = []
        
        # Extract final recommendation
        final_rec = analysis_results.get('final_recommendation', {})
        
        # Save each individual analyzer result
        analyses = analysis_results.get('analyses', {})
        for analysis_type, analysis_data in analyses.items():
            if analysis_data and not analysis_data.get('error'):
                predicted_price = analysis_data.get('predicted_price', 0) or 0
                # Handle infinity values
                if predicted_price == float('inf') or predicted_price == float('-inf'):
                    predicted_price = 0
                
                # Clean raw_data of infinity values
                clean_raw_data = self._clean_infinity_values(analysis_data)
                
                analysis_record = AnalysisHistory(
                    ticker=ticker,
                    analysis_type=analysis_type,
                    recommendation=analysis_data.get('recommendation', 'N/A'),
                    target_price=float(predicted_price),
                    confidence=analysis_data.get('confidence', 'N/A'),
                    raw_data=clean_raw_data,
                    scenario_context_id=scenario_context_id
                )
                db.add(analysis_record)
                saved_analyses.append(analysis_record)
        
        # Save consolidated final recommendation
        if final_rec:
            # Handle both object and dict formats
            if hasattr(final_rec, 'recommendation'):
                rec_value = final_rec.recommendation.value if hasattr(final_rec.recommendation, 'value') else str(final_rec.recommendation)
                target_price = getattr(final_rec, 'target_price', 0)
                confidence = getattr(final_rec, 'confidence', 'N/A')
            else:
                rec_value = final_rec.get('recommendation', 'N/A')
                target_price = final_rec.get('target_price', 0)
                confidence = final_rec.get('confidence', 'N/A')
            
            # Handle infinity values
            if target_price == float('inf') or target_price == float('-inf'):
                target_price = 0
            
            final_analysis = AnalysisHistory(
                ticker=ticker,
                analysis_type='final_recommendation',
                recommendation=rec_value,
                target_price=float(target_price) if target_price else 0,
                confidence=str(confidence),
                raw_data={
                    'final_recommendation': {
                        'recommendation': rec_value,
                        'target_price': float(target_price) if target_price else 0,
                        'confidence': str(confidence)
                    },
                    'company_type': analysis_results.get('company_type'),
                    'analyses_count': analysis_results.get('analyses_count', 0),
                    'execution_time_seconds': analysis_results.get('execution_time_seconds', 0)
                },
                scenario_context_id=scenario_context_id
            )
            db.add(final_analysis)
            saved_analyses.append(final_analysis)
        
        db.commit()
        for analysis in saved_analyses:
            db.refresh(analysis)
        
        return saved_analyses
    
    def get_latest_analysis(self, db: Session, ticker: str) -> Optional[dict]:
        """Get the most recent comprehensive analysis for a ticker"""
        # Get the latest final recommendation
        final_rec = db.query(AnalysisHistory).filter(
            AnalysisHistory.ticker == ticker,
            AnalysisHistory.analysis_type == 'final_recommendation'
        ).order_by(AnalysisHistory.analysis_date.desc()).first()
        
        if not final_rec:
            return None
        
        # Get all individual analyses from the same time period (within 1 hour)
        from sqlalchemy import and_
        time_window = final_rec.analysis_date
        individual_analyses = db.query(AnalysisHistory).filter(
            and_(
                AnalysisHistory.ticker == ticker,
                AnalysisHistory.analysis_type != 'final_recommendation',
                AnalysisHistory.analysis_date >= time_window - timedelta(hours=1),
                AnalysisHistory.analysis_date <= time_window + timedelta(hours=1)
            )
        ).all()
        
        # Reconstruct the comprehensive analysis
        result = {
            'ticker': ticker,
            'analysis_date': final_rec.analysis_date,
            'final_recommendation': final_rec.raw_data.get('final_recommendation', {}),
            'company_type': final_rec.raw_data.get('company_type'),
            'analyses_count': final_rec.raw_data.get('analyses_count', 0),
            'execution_time_seconds': final_rec.raw_data.get('execution_time_seconds', 0),
            'analyses': {}
        }
        
        # Add individual analyses
        for analysis in individual_analyses:
            result['analyses'][analysis.analysis_type] = analysis.raw_data
        
        return result
    
    def get_analysis_history(self, db: Session, ticker: str, 
                           analysis_type: Optional[str] = None,
                           limit: int = 10) -> List[AnalysisHistory]:
        """Get analysis history for a ticker"""
        query = db.query(AnalysisHistory).filter(AnalysisHistory.ticker == ticker)
        if analysis_type:
            query = query.filter(AnalysisHistory.analysis_type == analysis_type)
        return query.order_by(AnalysisHistory.analysis_date.desc()).limit(limit).all()
    
    def get_analysis_comparison(self, db: Session, ticker: str, 
                              days_back: int = 30) -> dict:
        """Compare analysis results over time for a ticker"""
        from sqlalchemy import and_
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        analyses = db.query(AnalysisHistory).filter(
            and_(
                AnalysisHistory.ticker == ticker,
                AnalysisHistory.analysis_date >= cutoff_date
            )
        ).order_by(AnalysisHistory.analysis_date.desc()).all()
        
        # Group by analysis type
        by_type = {}
        for analysis in analyses:
            if analysis.analysis_type not in by_type:
                by_type[analysis.analysis_type] = []
            by_type[analysis.analysis_type].append({
                'date': analysis.analysis_date,
                'recommendation': analysis.recommendation,
                'target_price': analysis.target_price,
                'confidence': analysis.confidence
            })
        
        return {
            'ticker': ticker,
            'period_days': days_back,
            'total_analyses': len(analyses),
            'by_type': by_type
        }
    
    def _clean_infinity_values(self, data):
        """Recursively clean infinity values from data structure"""
        import math
        
        if isinstance(data, dict):
            return {k: self._clean_infinity_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_infinity_values(item) for item in data]
        elif isinstance(data, float):
            if math.isinf(data) or math.isnan(data):
                return 0
            return data
        else:
            return data