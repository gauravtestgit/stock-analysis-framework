from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ...models.database import SessionLocal
from ...models.strategy_models import AnalysisHistory, InvestmentThesis
from sqlalchemy import desc, and_, func

class HistoricalAnalysisService:
    """Service for retrieving historical analysis data"""
    
    def get_stock_history(self, ticker: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get historical analyses for a stock"""
        db = SessionLocal()
        try:
            analyses = db.query(AnalysisHistory)\
                        .filter(AnalysisHistory.ticker == ticker)\
                        .order_by(desc(AnalysisHistory.analysis_date))\
                        .limit(limit)\
                        .all()
            
            return [self._format_analysis(analysis) for analysis in analyses]
        finally:
            db.close()
    
    def get_recommendation_timeline(self, ticker: str) -> List[Dict[str, Any]]:
        """Get recommendation changes over time"""
        db = SessionLocal()
        try:
            analyses = db.query(AnalysisHistory)\
                        .filter(AnalysisHistory.ticker == ticker)\
                        .order_by(AnalysisHistory.analysis_date)\
                        .all()
            
            timeline = []
            for analysis in analyses:
                timeline.append({
                    'date': analysis.analysis_date,
                    'analysis_type': analysis.analysis_type,
                    'recommendation': analysis.recommendation,
                    'target_price': analysis.target_price,
                    'current_price': analysis.current_price,
                    'confidence': analysis.confidence,
                    'batch_id': str(analysis.batch_analysis_id)
                })
            
            return timeline
        finally:
            db.close()
    
    def get_method_performance(self, ticker: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get performance by analysis method"""
        db = SessionLocal()
        try:
            analyses = db.query(AnalysisHistory)\
                        .filter(AnalysisHistory.ticker == ticker)\
                        .order_by(AnalysisHistory.analysis_date)\
                        .all()
            
            methods = {}
            for analysis in analyses:
                method = analysis.analysis_type
                if method not in methods:
                    methods[method] = []
                
                methods[method].append({
                    'date': analysis.analysis_date,
                    'recommendation': analysis.recommendation,
                    'target_price': analysis.target_price,
                    'confidence': analysis.confidence
                })
            
            return methods
        finally:
            db.close()
    
    def get_thesis_evolution(self, ticker: str) -> List[Dict[str, Any]]:
        """Get thesis evolution over time"""
        db = SessionLocal()
        try:
            theses = db.query(InvestmentThesis)\
                       .filter(InvestmentThesis.ticker == ticker)\
                       .order_by(desc(InvestmentThesis.created_at))\
                       .all()
            
            return [{
                'id': thesis.id,
                'date': thesis.created_at,
                'thesis_type': thesis.thesis_type,
                'content_preview': thesis.content[:200] + '...' if len(thesis.content) > 200 else thesis.content,
                'llm_provider': thesis.llm_provider,
                'llm_model': thesis.llm_model,
                'batch_analysis_id': str(thesis.batch_analysis_id) if thesis.batch_analysis_id else None
            } for thesis in theses]
        finally:
            db.close()
    
    def get_bulk_analysis_data(self, exchange: str = None, batch_job_id: str = None) -> Dict[str, Any]:
        """Get bulk analysis data for dashboard"""
        db = SessionLocal()
        try:
            # Get the most recent completed batch job
            from ...models.strategy_models import BatchJob
            
            if batch_job_id:
                # Get specific batch job by ID
                latest_batch = db.query(BatchJob).filter(
                    BatchJob.id == batch_job_id,
                    BatchJob.status == 'completed'
                ).first()
            else:
                # Get latest batch job
                query = db.query(BatchJob).filter(BatchJob.status == 'completed')
                if exchange:
                    query = query.filter(BatchJob.exchange == exchange)
                
                latest_batch = query.order_by(desc(BatchJob.completed_at)).first()
            
            if not latest_batch:
                return {'error': 'No completed batch jobs found', 'total_analyses': 0}
            
            # Get all analyses from this batch job
            analyses = db.query(AnalysisHistory)\
                        .filter(AnalysisHistory.batch_job_id == latest_batch.id)\
                        .all()
            
            if not analyses:
                return {'error': 'No analyses found for batch job', 'total_analyses': 0}
            
            # Get latest run info
            latest_run_info = {
                'batch_id': str(latest_batch.id),
                'batch_name': latest_batch.name,
                'exchange': latest_batch.exchange,
                'date': latest_batch.completed_at.strftime('%Y-%m-%d %H:%M'),
                'stock_count': latest_batch.total_stocks,
                'completed': latest_batch.completed_stocks,
                'failed': latest_batch.failed_stocks
            }
            
            # Exchange summary
            exchange_summary = self._calculate_exchange_summary(analyses)
            
            # Bullish convergence analysis
            convergence_analysis = self._calculate_convergence_analysis(analyses)
            
            # Method performance
            method_performance = self._calculate_method_performance(analyses)
            
            return {
                'latest_run_info': latest_run_info,
                'exchange_summary': exchange_summary,
                'convergence_analysis': convergence_analysis,
                'method_performance': method_performance,
                'total_analyses': len(analyses)
            }
        finally:
            db.close()
    
    def get_available_exchanges(self) -> Dict[str, Any]:
        """Get available exchanges from completed batch jobs"""
        db = SessionLocal()
        try:
            from ...models.strategy_models import BatchJob
            
            # Get distinct exchanges from completed batch jobs
            batches = db.query(BatchJob.exchange, func.count(BatchJob.id))\
                       .filter(BatchJob.status == 'completed')\
                       .group_by(BatchJob.exchange)\
                       .all()
            
            if not batches:
                return {}
            
            return {exchange: count for exchange, count in batches if exchange}
        finally:
            db.close()
    
    def get_batch_jobs_by_exchange(self, exchange: str = None) -> List[Dict[str, Any]]:
        """Get all completed batch jobs for an exchange with stock counts"""
        db = SessionLocal()
        try:
            from ...models.strategy_models import BatchJob
            
            query = db.query(BatchJob).filter(BatchJob.status == 'completed')
            if exchange:
                query = query.filter(BatchJob.exchange == exchange)
            
            batches = query.order_by(desc(BatchJob.completed_at)).all()
            
            return [{
                'batch_id': str(batch.id),
                'batch_name': batch.name,
                'exchange': batch.exchange,
                'completed_at': batch.completed_at.strftime('%Y-%m-%d %H:%M'),
                'total_stocks': batch.total_stocks,
                'completed_stocks': batch.completed_stocks,
                'failed_stocks': batch.failed_stocks,
                'created_by': batch.created_by
            } for batch in batches]
        finally:
            db.close()
    
    def _calculate_exchange_summary(self, analyses: List[AnalysisHistory]) -> List[Dict[str, Any]]:
        """Calculate exchange-level summary statistics"""
        exchange_data = {}
        
        for analysis in analyses:
            # Extract exchange from ticker (simplified logic)
            exchange = self._get_exchange_from_ticker(analysis.ticker)
            
            if exchange not in exchange_data:
                exchange_data[exchange] = {
                    'exchange': exchange,
                    'total_stocks': set(),
                    'bullish_count': 0,
                    'bearish_count': 0,
                    'neutral_count': 0,
                    'convergent_count': 0,
                    'confidence_sum': 0,
                    'confidence_count': 0
                }
            
            exchange_data[exchange]['total_stocks'].add(analysis.ticker)
            
            if analysis.recommendation in ['Buy', 'Strong Buy']:
                exchange_data[exchange]['bullish_count'] += 1
            elif analysis.recommendation in ['Sell', 'Strong Sell']:
                exchange_data[exchange]['bearish_count'] += 1
            else:
                exchange_data[exchange]['neutral_count'] += 1
            
            # Convert confidence to float if it's a string
            confidence_val = None
            if analysis.confidence:
                try:
                    confidence_val = float(analysis.confidence) if isinstance(analysis.confidence, str) else analysis.confidence
                except (ValueError, TypeError):
                    confidence_val = None
            
            if confidence_val and confidence_val >= 80:
                exchange_data[exchange]['convergent_count'] += 1
            
            if confidence_val:
                exchange_data[exchange]['confidence_sum'] += confidence_val
                exchange_data[exchange]['confidence_count'] += 1
        
        # Convert to list format
        result = []
        for exchange, data in exchange_data.items():
            result.append({
                'exchange': exchange,
                'total_stocks': len(data['total_stocks']),
                'bullish_count': data['bullish_count'],
                'bearish_count': data['bearish_count'],
                'neutral_count': data['neutral_count'],
                'convergent_count': data['convergent_count'],
                'avg_confidence': data['confidence_sum'] / data['confidence_count'] if data['confidence_count'] > 0 else 0
            })
        
        return result
    
    def _calculate_convergence_analysis(self, analyses: List[AnalysisHistory]) -> List[Dict[str, Any]]:
        """Calculate bullish convergence analysis with analyst alignment (20% threshold)"""
        # Group by ticker AND batch_analysis_id to avoid duplicates across batches
        ticker_batch_data = {}
        
        for analysis in analyses:
            key = (analysis.ticker, analysis.batch_analysis_id)
            if key not in ticker_batch_data:
                ticker_batch_data[key] = []
            ticker_batch_data[key].append(analysis)
        
        # Now group by ticker only, taking the most recent batch_analysis_id
        ticker_data = {}
        for (ticker, batch_analysis_id), analyses_list in ticker_batch_data.items():
            if ticker not in ticker_data:
                ticker_data[ticker] = analyses_list
            else:
                # Keep the analyses with the most recent analysis_date
                existing_date = max(a.analysis_date for a in ticker_data[ticker])
                new_date = max(a.analysis_date for a in analyses_list)
                if new_date > existing_date:
                    ticker_data[ticker] = analyses_list
        
        convergence_results = []
        
        for ticker, ticker_analyses in ticker_data.items():
            # Find analyst_consensus and final_recommendation analyses
            analyst_analysis = None
            final_recommendation_analysis = None
            current_price = None
            
            for analysis in ticker_analyses:
                if analysis.analysis_type == 'analyst_consensus':
                    analyst_analysis = analysis
                elif analysis.analysis_type == 'final_recommendation':
                    final_recommendation_analysis = analysis
                if analysis.current_price:
                    current_price = analysis.current_price
            
            if not current_price or current_price <= 0:
                continue
            
            # Calculate analyst upside if available
            analyst_upside = None
            analyst_count = 0
            if analyst_analysis and analyst_analysis.target_price and analyst_analysis.target_price > 0:
                analyst_upside = ((analyst_analysis.target_price - current_price) / current_price * 100)
                # Try to get analyst count from raw_data
                if analyst_analysis.raw_data and isinstance(analyst_analysis.raw_data, dict):
                    analyst_count = analyst_analysis.raw_data.get('num_analysts') or analyst_analysis.raw_data.get('analyst_count', 0)
            
            # Analyze each method for alignment
            aligned_methods = []
            method_details = {}
            
            for analysis in ticker_analyses:
                # Skip analyst_consensus and final_recommendation in convergence check
                if analysis.analysis_type in ['analyst_consensus', 'final_recommendation']:
                    continue
                
                if not analysis.target_price or analysis.target_price <= 0:
                    continue
                
                our_upside = ((analysis.target_price - current_price) / current_price * 100)
                
                # MODE 1: Analyst alignment (if analyst data available)
                if analyst_upside is not None:
                    # Check for bullish convergence (both >= 20% upside)
                    if our_upside >= 20 and analyst_upside >= 20:
                        deviation = abs(our_upside - analyst_upside)
                        
                        if deviation <= 10:
                            alignment = 'Precise_Aligned'
                        elif deviation <= 25:
                            alignment = 'Moderate_Aligned'
                        else:
                            alignment = 'Investment_Aligned'
                        
                        aligned_methods.append(analysis.analysis_type)
                        method_details[analysis.analysis_type] = {
                            'our_upside': round(our_upside, 1),
                            'target_price': analysis.target_price,
                            'alignment': alignment,
                            'deviation': round(deviation, 1)
                        }
                # MODE 2: Internal method convergence (no analyst data)
                else:
                    if our_upside >= 20:
                        aligned_methods.append(analysis.analysis_type)
                        method_details[analysis.analysis_type] = {
                            'our_upside': round(our_upside, 1),
                            'target_price': analysis.target_price
                        }
            
            # Require at least 1 method for analyst alignment, 2 methods for internal convergence
            min_methods = 1 if analyst_upside is not None else 2
            
            if len(aligned_methods) >= min_methods:
                avg_our_upside = sum(method_details[m]['our_upside'] for m in aligned_methods) / len(aligned_methods)
                avg_target = sum(method_details[m]['target_price'] for m in aligned_methods) / len(aligned_methods)
                
                # Get analyst target and quant target
                analyst_target = analyst_analysis.target_price if analyst_analysis else None
                quant_target = final_recommendation_analysis.target_price if final_recommendation_analysis else None
                
                convergence_results.append({
                    'ticker': ticker,
                    'converging_methods': len(aligned_methods),
                    'methods_list': ', '.join([m.upper() for m in aligned_methods]),
                    'our_upside': round(avg_our_upside, 1),
                    'analyst_upside': round(analyst_upside, 1) if analyst_upside is not None else None,
                    'analyst_count': analyst_count,
                    'analyst_target': round(analyst_target, 2) if analyst_target else None,
                    'quant_target': round(quant_target, 2) if quant_target else None,
                    'target_price': round(avg_target, 2),
                    'current_price': round(current_price, 2),
                    'method_details': method_details
                })
        
        # Sort by number of converging methods, then by our upside
        convergence_results.sort(key=lambda x: (x['converging_methods'], x['our_upside']), reverse=True)
        
        return convergence_results
    
    def _calculate_method_performance(self, analyses: List[AnalysisHistory]) -> Dict[str, List[Dict[str, Any]]]:
        """Calculate performance by analysis method"""
        method_data = {}
        
        for analysis in analyses:
            method = analysis.analysis_type
            if method not in method_data:
                method_data[method] = []
            
            upside_potential = 0
            if analysis.target_price and analysis.current_price and analysis.current_price > 0:
                upside_potential = (analysis.target_price - analysis.current_price) / analysis.current_price * 100
            
            # Convert confidence to float
            confidence_val = 0
            if analysis.confidence:
                try:
                    confidence_val = float(analysis.confidence) if isinstance(analysis.confidence, str) else analysis.confidence
                except (ValueError, TypeError):
                    confidence_val = 0
            
            method_data[method].append({
                'ticker': analysis.ticker,
                'recommendation': analysis.recommendation,
                'upside_potential': upside_potential,
                'confidence': confidence_val,
                'target_price': analysis.target_price or 0,
                'current_price': analysis.current_price or 0,
                'date': analysis.analysis_date
            })
        
        return method_data
    
    def _get_exchange_from_ticker(self, ticker: str) -> str:
        """Extract exchange from ticker (simplified logic)"""
        # This is a simplified approach - in reality you'd have a proper mapping
        if '.' in ticker:
            if ticker.endswith('.AX'):
                return 'ASX'
            elif ticker.endswith('.L'):
                return 'LSE'
            else:
                return 'OTHER'
        else:
            # Assume US exchanges for simple tickers
            return 'NASDAQ/NYSE'
    
    def _format_analysis(self, analysis: AnalysisHistory) -> Dict[str, Any]:
        """Format analysis for display"""
        return {
            'id': analysis.id,
            'date': analysis.analysis_date,
            'analysis_type': analysis.analysis_type,
            'recommendation': analysis.recommendation,
            'target_price': analysis.target_price,
            'current_price': analysis.current_price,
            'confidence': analysis.confidence,
            'batch_id': str(analysis.batch_analysis_id),
            'raw_data': analysis.raw_data
        }