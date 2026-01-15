from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import uuid

class StockInfo(Base):
    """Stock information table"""
    __tablename__ = "stock_info"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    security_name = Column(String(500), nullable=False)
    exchange = Column(String(10), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (UniqueConstraint('symbol', name='uq_stock_symbol'),)

class Scenario(Base):
    """Investment scenarios (US-China Trade War, Tech Regulation, etc.)"""
    __tablename__ = "scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # geopolitical, regulatory, economic
    base_probability = Column(Float, default=0.5)
    current_probability = Column(Float, default=0.5)
    timeframe = Column(String(20))  # 1M, 3M, 6M, 1Y, 2Y
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    outcomes = relationship("ScenarioOutcome", back_populates="scenario")
    strategy_scenarios = relationship("StrategyScenario", back_populates="scenario")
    probability_history = relationship("ScenarioProbabilityHistory", back_populates="scenario")

class ScenarioOutcome(Base):
    """Possible outcomes for each scenario"""
    __tablename__ = "scenario_outcomes"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"))
    name = Column(String(100), nullable=False)
    probability = Column(Float, default=0.5)
    impact_description = Column(Text)
    expected_duration = Column(String(20))
    
    # Relationships
    scenario = relationship("Scenario", back_populates="outcomes")

class Strategy(Base):
    """Investment strategies"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(50))  # scenario_based, momentum, value
    timeframe = Column(String(20))  # 1M, 3M, 6M, 1Y
    risk_tolerance = Column(String(20))  # conservative, moderate, aggressive
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="strategy")
    strategy_scenarios = relationship("StrategyScenario", back_populates="strategy")
    performance_history = relationship("StrategyPerformance", back_populates="strategy")

class StrategyScenario(Base):
    """Mapping between strategies and scenarios"""
    __tablename__ = "strategy_scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    scenario_id = Column(Integer, ForeignKey("scenarios.id"))
    weight = Column(Float, default=1.0)  # How much this scenario affects strategy
    impact_factor = Column(Float, default=1.0)  # Multiplier for this scenario
    
    # Relationships
    strategy = relationship("Strategy", back_populates="strategy_scenarios")
    scenario = relationship("Scenario", back_populates="strategy_scenarios")

class Portfolio(Base):
    """Investment portfolios implementing strategies"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    name = Column(String(100), nullable=False)
    total_value = Column(Float, default=0.0)
    cash_balance = Column(Float, default=0.0)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio")
    rebalancing_events = relationship("RebalancingEvent", back_populates="portfolio")

class Position(Base):
    """Individual stock positions in portfolios"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    ticker = Column(String(10), nullable=False)
    shares = Column(Float, default=0.0)
    avg_cost_basis = Column(Float, default=0.0)
    current_price = Column(Float, default=0.0)
    market_value = Column(Float, default=0.0)
    target_weight = Column(Float, default=0.0)  # Target % of portfolio
    scenario_adjustment = Column(Float, default=1.0)  # Adjustment factor for scenarios
    last_rebalanced_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")
    trades = relationship("Trade", back_populates="position")

class BatchJob(Base):
    """Batch analysis job tracking"""
    __tablename__ = "batch_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(200))  # e.g., "NASDAQ Analysis 2024-01-15"
    exchange = Column(String(50), index=True)  # NASDAQ, NYSE, ASX, etc.
    status = Column(String(20), default="pending", index=True)  # pending, running, completed, failed
    total_stocks = Column(Integer, default=0)
    completed_stocks = Column(Integer, default=0)
    failed_stocks = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    created_by = Column(String(100))  # user who initiated
    input_file = Column(String(500))  # path to input CSV
    output_file = Column(String(500))  # path to output CSV
    
    # Relationships
    analyses = relationship("AnalysisHistory", back_populates="batch_job")

class AnalysisHistory(Base):
    """Historical analysis results for tracking changes over time"""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    analysis_date = Column(DateTime, default=datetime.utcnow, index=True)
    analysis_type = Column(String(50))  # dcf, technical, ai_insights
    recommendation = Column(String(20))  # Buy, Hold, Sell
    target_price = Column(Float)
    current_price = Column(Float)  # Price at time of analysis
    confidence = Column(String(20))
    raw_data = Column(JSON)  # Full analysis result
    scenario_context_id = Column(Integer, ForeignKey("scenarios.id"))
    batch_analysis_id = Column(UUID(as_uuid=True), index=True)  # UUID for grouping analysis methods per stock
    batch_job_id = Column(UUID(as_uuid=True), ForeignKey("batch_jobs.id"), index=True)  # Link to batch job
    
    # Relationships
    scenario_context = relationship("Scenario")
    batch_job = relationship("BatchJob", back_populates="analyses")
    theses = relationship("InvestmentThesis", primaryjoin="AnalysisHistory.batch_analysis_id == InvestmentThesis.batch_analysis_id", foreign_keys="[InvestmentThesis.batch_analysis_id]", back_populates="analysis_data")

class StrategyPerformance(Base):
    """Strategy performance tracking over time"""
    __tablename__ = "strategy_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    date = Column(DateTime, default=datetime.utcnow)
    portfolio_value = Column(Float)
    benchmark_value = Column(Float)  # S&P 500 or other benchmark
    daily_return = Column(Float)
    cumulative_return = Column(Float)
    drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="performance_history")

class NewsEvent(Base):
    """News events that trigger scenario updates"""
    __tablename__ = "news_events"
    
    id = Column(Integer, primary_key=True, index=True)
    headline = Column(Text, nullable=False)
    source = Column(String(100))
    published_at = Column(DateTime)
    sentiment_score = Column(Float)
    relevance_score = Column(Float)
    scenario_impact = Column(JSON)  # Which scenarios affected and how
    processed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    probability_updates = relationship("ScenarioProbabilityHistory", back_populates="trigger_event")

class ScenarioProbabilityHistory(Base):
    """Historical tracking of scenario probability changes"""
    __tablename__ = "scenario_probability_history"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"))
    date = Column(DateTime, default=datetime.utcnow)
    probability = Column(Float)
    trigger_event_id = Column(Integer, ForeignKey("news_events.id"))
    reason = Column(Text)
    
    # Relationships
    scenario = relationship("Scenario", back_populates="probability_history")
    trigger_event = relationship("NewsEvent", back_populates="probability_updates")

class RebalancingEvent(Base):
    """Portfolio rebalancing events"""
    __tablename__ = "rebalancing_events"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    trigger_type = Column(String(50))  # scheduled, scenario_change, threshold
    trigger_reason = Column(Text)
    executed_at = Column(DateTime, default=datetime.utcnow)
    total_trades = Column(Integer, default=0)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="rebalancing_events")
    trades = relationship("Trade", back_populates="rebalancing_event")

class Trade(Base):
    """Individual trades executed during rebalancing"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    rebalancing_event_id = Column(Integer, ForeignKey("rebalancing_events.id"))
    position_id = Column(Integer, ForeignKey("positions.id"))
    ticker = Column(String(10), nullable=False)
    action = Column(String(10))  # buy, sell
    shares = Column(Float)
    price = Column(Float)
    total_value = Column(Float)
    reason = Column(Text)
    executed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    rebalancing_event = relationship("RebalancingEvent", back_populates="trades")
    position = relationship("Position", back_populates="trades")

class InvestmentThesis(Base):
    """Generated investment theses storage"""
    __tablename__ = "investment_theses"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    thesis_type = Column(String(50), nullable=False)  # bull_case, bear_case, balanced
    content = Column(Text, nullable=False)
    llm_provider = Column(String(50))  # openai, anthropic, groq
    llm_model = Column(String(100))  # gpt-4, claude-3, etc
    prompt_template = Column(String(100))  # prompt file used
    batch_analysis_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Link to analysis batch UUID
    previous_thesis_id = Column(Integer, ForeignKey("investment_theses.id"))  # for chaining
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    previous_thesis = relationship("InvestmentThesis", remote_side=[id])
    analysis_data = relationship("AnalysisHistory", primaryjoin="InvestmentThesis.batch_analysis_id == AnalysisHistory.batch_analysis_id", foreign_keys="[InvestmentThesis.batch_analysis_id]", back_populates="theses")