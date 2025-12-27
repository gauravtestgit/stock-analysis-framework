import asyncio
from typing import Dict, Any, List, Optional
from ..services.orchestration.analysis_orchestrator import AnalysisOrchestrator
from ..services.storage.analysis_storage_service import AnalysisStorageService
from ..implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..implementations.analyzers.startup_analyzer import StartupAnalyzer
from ..implementations.analyzers.comparable_analyzer import ComparableAnalyzer
from ..implementations.analyzers.ai_insights_analyzer import AIInsightsAnalyzer
from ..implementations.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
from ..implementations.analyzers.business_model_analyzer import BusinessModelAnalyzer
from ..implementations.analyzers.competitive_position_analyzer import CompetitivePositionAnalyzer
from ..implementations.analyzers.management_quality_analyzer import ManagementQualityAnalyzer
from ..implementations.analyzers.financial_health_analyzer import FinancialHealthAnalyzer
from ..implementations.analyzers.analyst_consensus_analyzer import AnalystConsensusAnalyzer
from ..implementations.data_providers.sec_edgar_provider import SECEdgarProvider
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.classifier import CompanyClassifier
from ..models.analysis_result import AnalysisType
from .models import AnalyzerInfo

class AnalysisService:
    """Service layer for stock analysis API"""
    
    def __init__(self, save_to_db: bool = True, debug_mode: bool = False, max_news_articles: int = 5):
        self.data_provider = YahooFinanceProvider()
        self.classifier = CompanyClassifier()
        self.quality_calculator = QualityScoreCalculator()
        self.save_to_db = save_to_db
        self.debug_mode = debug_mode
        self.max_news_articles = max_news_articles
        self.storage_service = AnalysisStorageService() if save_to_db else None
        # Don't create default orchestrator - create on demand
        self._default_orchestrator = None
    
    def _setup_orchestrator(self) -> AnalysisOrchestrator:
        """Setup orchestrator with all analyzers"""
        orchestrator = AnalysisOrchestrator(
            self.data_provider, 
            self.classifier, 
            self.quality_calculator,
            self.debug_mode
        )
        
        # Register quantitative analyzers
        orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer())
        orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
        orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer())
        orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer())
        
        # Register qualitative analyzers
        orchestrator.register_analyzer(AnalysisType.AI_INSIGHTS, AIInsightsAnalyzer(self.data_provider))
        orchestrator.register_analyzer(AnalysisType.NEWS_SENTIMENT, NewsSentimentAnalyzer(self.data_provider, debug_mode=self.debug_mode, enable_web_scraping=True, max_articles=self.max_news_articles))
        orchestrator.register_analyzer(AnalysisType.BUSINESS_MODEL, BusinessModelAnalyzer(self.data_provider))
        orchestrator.register_analyzer(AnalysisType.COMPETITIVE_POSITION, CompetitivePositionAnalyzer(self.data_provider))
        orchestrator.register_analyzer(AnalysisType.MANAGEMENT_QUALITY, ManagementQualityAnalyzer(self.data_provider))
        orchestrator.register_analyzer(AnalysisType.ANALYST_CONSENSUS, AnalystConsensusAnalyzer(self.data_provider))
        
        # Register SEC-based analyzer
        sec_provider = SECEdgarProvider()
        orchestrator.register_analyzer(AnalysisType.FINANCIAL_HEALTH, FinancialHealthAnalyzer(sec_provider))
        
        return orchestrator
    
    async def analyze_stock(self, ticker: str, enabled_analyzers: Optional[List[str]] = None, llm_provider: Optional[str] = None, llm_model: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive stock analysis"""
        # Create selective orchestrator if specific analyzers requested
        if enabled_analyzers:
            orchestrator = self._create_selective_orchestrator(enabled_analyzers, llm_provider, llm_model)
        else:
            orchestrator = self._create_orchestrator_with_llm(llm_provider, llm_model)
        
        # Run analysis in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, orchestrator.analyze_stock, ticker)
        
        # Convert final_recommendation object to dict if present
        if 'final_recommendation' in result and result['final_recommendation']:
            final_rec = result['final_recommendation']
            if hasattr(final_rec, '__dict__'):
                # Convert Recommendation object to dict with correct field names
                recommendation_value = getattr(final_rec, 'recommendation', 'Hold')
                if hasattr(recommendation_value, 'value'):
                    recommendation_value = recommendation_value.value
                
                result['final_recommendation'] = {
                    'ticker': getattr(final_rec, 'ticker', ticker),
                    'recommendation': recommendation_value,
                    'consensus_score': getattr(final_rec, 'upside_potential', 0.0),
                    'target_price': getattr(final_rec, 'target_price', 0.0),
                    'confidence': getattr(final_rec, 'confidence', 'Medium'),
                    'contributing_analyses': getattr(final_rec, 'bullish_signals', []) + getattr(final_rec, 'bearish_signals', []),
                    'reasoning': getattr(final_rec, 'summary', ''),
                    'risk_level': getattr(final_rec, 'risk_level', 'Medium'),
                    'key_risks': getattr(final_rec, 'key_risks', [])
                }
        
        # Store in database if enabled
        if 'error' not in result and self.save_to_db and self.storage_service:
            self.storage_service.store_comprehensive_analysis(ticker, result)
        
        return result
    
    def _create_orchestrator_with_llm(self, llm_provider: Optional[str] = None, llm_model: Optional[str] = None) -> AnalysisOrchestrator:
        """Create orchestrator with LLM configuration"""
        if llm_provider and llm_model:
            # Import LLM manager here to avoid circular imports
            from ..implementations.llm_providers.llm_manager import LLMManager
            
            # Create LLM manager with specified provider/model
            llm_manager = LLMManager(use_plugin_system=True)
            llm_manager.set_primary_provider(llm_provider, llm_model)
            
            # Create orchestrator with LLM manager
            orchestrator = AnalysisOrchestrator(
                self.data_provider, 
                self.classifier, 
                self.quality_calculator,
                self.debug_mode
            )
            
            # Register analyzers with shared LLM manager
            orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer())
            orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
            orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer())
            orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer())
            
            # Register qualitative analyzers with shared LLM manager
            orchestrator.register_analyzer(AnalysisType.AI_INSIGHTS, AIInsightsAnalyzer(self.data_provider, llm_manager))
            orchestrator.register_analyzer(AnalysisType.NEWS_SENTIMENT, NewsSentimentAnalyzer(self.data_provider, llm_manager, debug_mode=self.debug_mode, enable_web_scraping=True, max_articles=self.max_news_articles))
            orchestrator.register_analyzer(AnalysisType.BUSINESS_MODEL, BusinessModelAnalyzer(self.data_provider, llm_manager))
            orchestrator.register_analyzer(AnalysisType.COMPETITIVE_POSITION, CompetitivePositionAnalyzer(self.data_provider))
            orchestrator.register_analyzer(AnalysisType.MANAGEMENT_QUALITY, ManagementQualityAnalyzer(self.data_provider))
            orchestrator.register_analyzer(AnalysisType.ANALYST_CONSENSUS, AnalystConsensusAnalyzer(self.data_provider))
            
            # Register SEC-based analyzer
            sec_provider = SECEdgarProvider()
            orchestrator.register_analyzer(AnalysisType.FINANCIAL_HEALTH, FinancialHealthAnalyzer(sec_provider))
            
            return orchestrator
        else:
            # Create default orchestrator with legacy system
            if not self._default_orchestrator:
                self._default_orchestrator = self._setup_orchestrator()
            return self._default_orchestrator
    
    def _create_selective_orchestrator(self, enabled_analyzers: List[str], llm_provider: Optional[str] = None, llm_model: Optional[str] = None) -> AnalysisOrchestrator:
        """Create orchestrator with only selected analyzers"""
        orchestrator = AnalysisOrchestrator(
            self.data_provider, 
            self.classifier, 
            self.quality_calculator,
            self.debug_mode
        )
        
        # Create LLM manager if provider/model specified
        llm_manager = None
        if llm_provider and llm_model:
            from ..implementations.llm_providers.llm_manager import LLMManager
            llm_manager = LLMManager(use_plugin_system=True)
            llm_manager.set_primary_provider(llm_provider, llm_model)
        
        # Analyzer mapping with LLM manager support
        analyzer_map = {
            'dcf': (AnalysisType.DCF, DCFAnalyzer()),
            'technical': (AnalysisType.TECHNICAL, TechnicalAnalyzer()),
            'comparable': (AnalysisType.COMPARABLE, ComparableAnalyzer()),
            'startup': (AnalysisType.STARTUP, StartupAnalyzer()),
            'ai_insights': (AnalysisType.AI_INSIGHTS, AIInsightsAnalyzer(self.data_provider, llm_manager) if llm_manager else AIInsightsAnalyzer(self.data_provider)),
            'news_sentiment': (AnalysisType.NEWS_SENTIMENT, NewsSentimentAnalyzer(self.data_provider, llm_manager, debug_mode=self.debug_mode, enable_web_scraping=True, max_articles=self.max_news_articles) if llm_manager else NewsSentimentAnalyzer(self.data_provider, debug_mode=self.debug_mode, enable_web_scraping=True, max_articles=self.max_news_articles)),
            'business_model': (AnalysisType.BUSINESS_MODEL, BusinessModelAnalyzer(self.data_provider, llm_manager) if llm_manager else BusinessModelAnalyzer(self.data_provider)),
            'competitive_position': (AnalysisType.COMPETITIVE_POSITION, CompetitivePositionAnalyzer(self.data_provider)),
            'management_quality': (AnalysisType.MANAGEMENT_QUALITY, ManagementQualityAnalyzer(self.data_provider)),
            'analyst_consensus': (AnalysisType.ANALYST_CONSENSUS, AnalystConsensusAnalyzer(self.data_provider)),
            'financial_health': (AnalysisType.FINANCIAL_HEALTH, FinancialHealthAnalyzer(SECEdgarProvider()))
        }
        
        # Register only requested analyzers
        for analyzer_name in enabled_analyzers:
            # Convert to lowercase for mapping
            analyzer_key = analyzer_name.lower()
            if analyzer_key in analyzer_map:
                analysis_type, analyzer = analyzer_map[analyzer_key]
                orchestrator.register_analyzer(analysis_type, analyzer)
        
        return orchestrator
    
    def get_available_analyzers(self) -> List[AnalyzerInfo]:
        """Get list of available analyzers"""
        analyzers = []
        
        analyzer_info = {
            'dcf': {'name': 'DCF Valuation', 'applicable_to': ['mature', 'growth', 'reit', 'commodity', 'cyclical']},
            'technical': {'name': 'Technical Analysis', 'applicable_to': ['all']},
            'comparable': {'name': 'Comparable Analysis', 'applicable_to': ['mature', 'growth', 'financial', 'reit', 'commodity', 'cyclical']},
            'startup': {'name': 'Startup Analysis', 'applicable_to': ['startup']},
            'ai_insights': {'name': 'AI Insights', 'applicable_to': ['all']},
            'news_sentiment': {'name': 'News Sentiment', 'applicable_to': ['all']},
            'business_model': {'name': 'Business Model', 'applicable_to': ['all']},
            'competitive_position': {'name': 'Competitive Position', 'applicable_to': ['all']},
            'management_quality': {'name': 'Management Quality', 'applicable_to': ['all']},
            'financial_health': {'name': 'Financial Health', 'applicable_to': ['all except ETF']},
            'analyst_consensus': {'name': 'Analyst Consensus', 'applicable_to': ['all']}
        }
        
        for analyzer_type in self.orchestrator.analyzers.keys():
            key = analyzer_type.value
            info = analyzer_info.get(key, {'name': key.title(), 'applicable_to': ['all']})
            
            analyzers.append(AnalyzerInfo(
                name=info['name'],
                enabled=True,
                applicable_to=info['applicable_to']
            ))
        
        return analyzers
    
    async def classify_company(self, ticker: str) -> Dict[str, Any]:
        """Classify company type"""
        try:
            # Get financial data
            financial_metrics = self.data_provider.get_financial_metrics(ticker)
            if 'error' in financial_metrics:
                return {'error': f"Failed to get financial data: {financial_metrics['error']}"}
            
            # Classify
            company_type = self.classifier.classify(ticker, financial_metrics)
            company_type_str = company_type.value if hasattr(company_type, 'value') else company_type
            
            return {
                'ticker': ticker,
                'company_type': company_type_str,
                'sector': financial_metrics.get('sector', 'Unknown'),
                'industry': financial_metrics.get('industry', 'Unknown')
            }
        except Exception as e:
            return {'error': str(e)}
    
    async def get_quality_score(self, ticker: str) -> Dict[str, Any]:
        """Get quality score only"""
        try:
            # Get financial data
            financial_metrics = self.data_provider.get_financial_metrics(ticker)
            if 'error' in financial_metrics:
                return {'error': f"Failed to get financial data: {financial_metrics['error']}"}
            
            # Calculate quality
            quality_result = self.quality_calculator.calculate(financial_metrics)
            
            return {
                'ticker': ticker,
                'quality_score': quality_result.get('quality_score', 0),
                'grade': quality_result.get('grade', 'N/A'),
                'data_quality': quality_result.get('data_quality', 'Unknown')
            }
        except Exception as e:
            return {'error': str(e)}