from sqlalchemy.orm import Session
from sqlalchemy import and_, func, distinct
from typing import List, Optional, Union
from datetime import datetime, timedelta
import math
import uuid
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
                                   scenario_context_id: Optional[int] = None,
                                   batch_analysis_id: Optional[Union[str, uuid.UUID]] = None) -> List[AnalysisHistory]:
        """Save comprehensive analysis results from multiple analyzers"""
        saved_analyses = []
        
        # Extract analyses first
        analyses = analysis_results.get('analyses', {})
        # print(f"DEBUG: Found {len(analyses)} analyses for {ticker}")
        
        # Extract current price from financial_metrics (primary source)
        current_price = analysis_results.get('financial_metrics', {}).get('current_price')
        if not current_price:
            # Fallback: extract from any analyzer that has it
            for analysis_data in analyses.values():
                if analysis_data and 'current_price' in analysis_data:
                    current_price = analysis_data['current_price']
                    break
        # print(f"DEBUG: Current price: {current_price}")
        
        # Extract final recommendation
        final_rec = analysis_results.get('final_recommendation', {})
        # print(f"DEBUG: Final recommendation exists: {bool(final_rec)}")
        
        # Save each individual analyzer result
        for analysis_type, analysis_data in analyses.items():
            # print(f"DEBUG: Processing {analysis_type}...")
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
                    current_price=current_price,
                    confidence=analysis_data.get('confidence', 'N/A'),
                    raw_data=clean_raw_data,
                    scenario_context_id=scenario_context_id,
                    batch_analysis_id=batch_analysis_id
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
                current_price=current_price,
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
                scenario_context_id=scenario_context_id,
                batch_analysis_id=batch_analysis_id
            )
            db.add(final_analysis)
            saved_analyses.append(final_analysis)
        
        if saved_analyses:
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
    
    def get_latest_analysis_by_exchange(self, db: Session, exchange: str = None, limit: int = None) -> List[AnalysisHistory]:
        """Get latest analysis for each ticker, optionally filtered by exchange"""
        
        # Subquery to get latest analysis date for each ticker
        latest_subquery = db.query(
            AnalysisHistory.ticker,
            func.max(AnalysisHistory.analysis_date).label('latest_date')
        ).filter(
            AnalysisHistory.analysis_type == 'final_recommendation'
        ).group_by(AnalysisHistory.ticker).subquery()
        
        # Main query to get full records for latest analyses
        query = db.query(AnalysisHistory).join(
            latest_subquery,
            and_(
                AnalysisHistory.ticker == latest_subquery.c.ticker,
                AnalysisHistory.analysis_date == latest_subquery.c.latest_date,
                AnalysisHistory.analysis_type == 'final_recommendation'
            )
        )
        
        # Apply exchange filter if provided
        if exchange:
            # Extract exchange from ticker format
            if exchange == 'ASX':
                query = query.filter(AnalysisHistory.ticker.like('%.ax'))
            elif exchange == 'NZX':
                query = query.filter(AnalysisHistory.ticker.like('%.nz'))
            elif exchange == 'NASDAQ':
                query = query.filter(
                    and_(
                        ~AnalysisHistory.ticker.like('%.%'),
                        func.length(AnalysisHistory.ticker) <= 4
                    )
                )
            elif exchange == 'NYSE':
                query = query.filter(
                    and_(
                        ~AnalysisHistory.ticker.like('%.%'),
                        func.length(AnalysisHistory.ticker) > 4
                    )
                )
        
        query = query.order_by(AnalysisHistory.analysis_date.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_analysis_summary_stats(self, db: Session) -> dict:
        """Get summary statistics of stored analysis"""
        
        # Total unique stocks analyzed
        total_stocks = db.query(func.count(distinct(AnalysisHistory.ticker))).filter(
            AnalysisHistory.analysis_type == 'final_recommendation'
        ).scalar()
        
        # Latest analysis info
        latest_analysis = db.query(AnalysisHistory).filter(
            AnalysisHistory.analysis_type == 'final_recommendation'
        ).order_by(AnalysisHistory.analysis_date.desc()).first()
        
        # Recommendation distribution (latest only)
        latest_subquery = db.query(
            AnalysisHistory.ticker,
            func.max(AnalysisHistory.analysis_date).label('latest_date')
        ).filter(
            AnalysisHistory.analysis_type == 'final_recommendation'
        ).group_by(AnalysisHistory.ticker).subquery()
        
        rec_distribution = db.query(
            AnalysisHistory.recommendation,
            func.count(AnalysisHistory.recommendation)
        ).join(
            latest_subquery,
            and_(
                AnalysisHistory.ticker == latest_subquery.c.ticker,
                AnalysisHistory.analysis_date == latest_subquery.c.latest_date,
                AnalysisHistory.analysis_type == 'final_recommendation'
            )
        ).group_by(AnalysisHistory.recommendation).all()
        
        # Exchange distribution
        exchange_counts = {}
        latest_analyses = db.query(AnalysisHistory).join(
            latest_subquery,
            and_(
                AnalysisHistory.ticker == latest_subquery.c.ticker,
                AnalysisHistory.analysis_date == latest_subquery.c.latest_date,
                AnalysisHistory.analysis_type == 'final_recommendation'
            )
        ).all()
        
        for analysis in latest_analyses:
            exchange = self._determine_exchange_from_ticker(analysis.ticker)
            exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
        
        return {
            'total_stocks': total_stocks,
            'latest_analysis_date': latest_analysis.analysis_date if latest_analysis else None,
            'recommendation_distribution': dict(rec_distribution),
            'exchange_distribution': exchange_counts
        }
    
    def search_analysis_results(self, db: Session, 
                               recommendation: str = None,
                               exchange: str = None,
                               min_target_price: float = None,
                               max_target_price: float = None,
                               limit: int = 100) -> List[AnalysisHistory]:
        """Search analysis results with various filters"""
        
        # Subquery for latest analyses
        latest_subquery = db.query(
            AnalysisHistory.ticker,
            func.max(AnalysisHistory.analysis_date).label('latest_date')
        ).filter(
            AnalysisHistory.analysis_type == 'final_recommendation'
        ).group_by(AnalysisHistory.ticker).subquery()
        
        # Main query
        query = db.query(AnalysisHistory).join(
            latest_subquery,
            and_(
                AnalysisHistory.ticker == latest_subquery.c.ticker,
                AnalysisHistory.analysis_date == latest_subquery.c.latest_date,
                AnalysisHistory.analysis_type == 'final_recommendation'
            )
        )
        
        # Apply filters
        if recommendation:
            query = query.filter(AnalysisHistory.recommendation == recommendation)
        
        if exchange:
            if exchange == 'ASX':
                query = query.filter(AnalysisHistory.ticker.like('%.ax'))
            elif exchange == 'NZX':
                query = query.filter(AnalysisHistory.ticker.like('%.nz'))
            elif exchange == 'NASDAQ':
                query = query.filter(
                    and_(
                        ~AnalysisHistory.ticker.like('%.%'),
                        func.length(AnalysisHistory.ticker) <= 4
                    )
                )
            elif exchange == 'NYSE':
                query = query.filter(
                    and_(
                        ~AnalysisHistory.ticker.like('%.%'),
                        func.length(AnalysisHistory.ticker) > 4
                    )
                )
        
        if min_target_price is not None:
            query = query.filter(AnalysisHistory.target_price >= min_target_price)
        
        if max_target_price is not None:
            query = query.filter(AnalysisHistory.target_price <= max_target_price)
        
        query = query.order_by(AnalysisHistory.target_price.desc()).limit(limit)
        
        return query.all()
    
    def _determine_exchange_from_ticker(self, ticker: str) -> str:
        """Determine exchange based on ticker format"""
        if ticker.endswith('.ax'):
            return 'ASX'
        elif ticker.endswith('.nz'):
            return 'NZX'
        elif len(ticker) <= 4 and ticker.isupper() and '.' not in ticker:
            return 'NASDAQ'
        else:
            return 'NYSE'
    
    def get_all_stocks(self, db: Session) -> List['StockInfo']:
        """Get all stocks from stock_info table"""
        from ...models.strategy_models import StockInfo
        return db.query(StockInfo).order_by(StockInfo.symbol).all()
    
    def upsert_stock(self, db: Session, symbol: str, security_name: str, exchange: str) -> 'StockInfo':
        """Insert or update stock information"""
        from ...models.strategy_models import StockInfo
        
        stock = db.query(StockInfo).filter(StockInfo.symbol == symbol).first()
        if stock:
            stock.security_name = security_name
            stock.exchange = exchange
            stock.updated_at = datetime.utcnow()
        else:
            stock = StockInfo(
                symbol=symbol,
                security_name=security_name,
                exchange=exchange
            )
            db.add(stock)
        
        db.commit()
        db.refresh(stock)
        return stock
    
    def bulk_upsert_stocks(self, db: Session, stocks_data: List[dict]) -> int:
        """Bulk insert/update stock information"""
        from ...models.strategy_models import StockInfo
        
        count = 0
        for stock_data in stocks_data:
            self.upsert_stock(
                db, 
                stock_data['symbol'], 
                stock_data['security_name'], 
                stock_data['exchange']
            )
            count += 1
        
        return count
    
    def _clean_infinity_values(self, data):
        """Recursively clean infinity values from data structure"""
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