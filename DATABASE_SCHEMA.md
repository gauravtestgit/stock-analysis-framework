# Database Schema Documentation

## Overview
The finance application uses a comprehensive database structure to support portfolio management, strategy backtesting, scenario analysis, and performance tracking.

## Core Tables

### 1. analysis_history
**Purpose**: Stores all comprehensive analysis results from batch processing and individual stock analysis
- `id` (Primary Key)
- `ticker` (VARCHAR) - Stock symbol (NASDAQ, NYSE, ASX tickers)
- `analysis_date` (TIMESTAMP) - When analysis was performed
- `batch_id` (VARCHAR) - Batch identifier for bulk analysis runs
- `exchange` (VARCHAR) - Stock exchange (NASDAQ, NYSE, ASX)
- `company_type` (VARCHAR) - Classified company type (growth_profitable, mature_profitable, etc.)
- `quality_grade` (VARCHAR) - Data quality assessment (A, B, C, D)
- `final_recommendation` (VARCHAR) - Consolidated recommendation (Strong Buy, Buy, Hold, Sell, Strong Sell)
- `target_price` (DECIMAL) - Consensus target price from all methods
- `confidence` (VARCHAR) - Overall analysis confidence level
- `upside_potential` (DECIMAL) - Percentage upside to target price
- `risk_level` (VARCHAR) - Risk assessment (Low, Medium, High)
- `dcf_recommendation` (VARCHAR) - DCF analysis recommendation
- `technical_recommendation` (VARCHAR) - Technical analysis recommendation
- `comparable_recommendation` (VARCHAR) - Comparable company recommendation
- `ai_insights_recommendation` (VARCHAR) - AI insights recommendation
- `news_sentiment_recommendation` (VARCHAR) - News sentiment recommendation
- `business_model_recommendation` (VARCHAR) - Business model recommendation
- `competitive_position_recommendation` (VARCHAR) - Competitive position recommendation
- `management_quality_recommendation` (VARCHAR) - Management quality recommendation
- `analyst_consensus_recommendation` (VARCHAR) - Analyst consensus recommendation
- `industry_analysis_recommendation` (VARCHAR) - Industry analysis recommendation
- `analysis_data` (JSON/TEXT) - Complete analysis results with all method details
- `execution_time_seconds` (DECIMAL) - Time taken to complete analysis
- `analyses_count` (INTEGER) - Number of analysis methods successfully executed

### 2. news_events
**Purpose**: Tracks significant news events and their market impact
- `id` (Primary Key)
- `ticker` (VARCHAR) - Affected stock symbol
- `event_date` (TIMESTAMP) - When news occurred
- `event_type` (VARCHAR) - Category of news (earnings, merger, etc.)
- `headline` (TEXT) - News headline
- `sentiment_score` (DECIMAL) - Sentiment analysis score (-1 to 1)
- `market_impact` (DECIMAL) - Price impact percentage
- `source` (VARCHAR) - News source

### 3. portfolios
**Purpose**: Defines investment portfolios
- `id` (Primary Key)
- `name` (VARCHAR) - Portfolio name
- `description` (TEXT) - Portfolio description
- `created_date` (TIMESTAMP) - Creation date
- `initial_value` (DECIMAL) - Starting portfolio value
- `current_value` (DECIMAL) - Current portfolio value
- `strategy_id` (Foreign Key) - Associated strategy

### 4. positions
**Purpose**: Individual stock positions within portfolios
- `id` (Primary Key)
- `portfolio_id` (Foreign Key) - Parent portfolio
- `ticker` (VARCHAR) - Stock symbol
- `shares` (DECIMAL) - Number of shares held
- `entry_price` (DECIMAL) - Purchase price per share
- `entry_date` (TIMESTAMP) - Purchase date
- `current_price` (DECIMAL) - Latest price per share
- `unrealized_pnl` (DECIMAL) - Unrealized profit/loss

### 5. rebalancing_events
**Purpose**: Records portfolio rebalancing activities
- `id` (Primary Key)
- `portfolio_id` (Foreign Key) - Target portfolio
- `rebalance_date` (TIMESTAMP) - When rebalancing occurred
- `trigger_type` (VARCHAR) - What triggered rebalancing
- `old_allocation` (JSON) - Previous allocation percentages
- `new_allocation` (JSON) - New allocation percentages
- `transaction_costs` (DECIMAL) - Costs incurred

### 6. scenarios
**Purpose**: Defines market scenarios for stress testing
- `id` (Primary Key)
- `name` (VARCHAR) - Scenario name (e.g., "Market Crash", "Bull Run")
- `description` (TEXT) - Scenario details
- `probability` (DECIMAL) - Likelihood of occurrence (0-1)
- `duration_months` (INTEGER) - Expected scenario duration
- `market_impact` (JSON) - Sector/asset class impacts

### 7. scenario_outcomes
**Purpose**: Results of running scenarios against portfolios
- `id` (Primary Key)
- `portfolio_id` (Foreign Key) - Tested portfolio
- `scenario_id` (Foreign Key) - Applied scenario
- `simulation_date` (TIMESTAMP) - When simulation ran
- `final_value` (DECIMAL) - Portfolio value after scenario
- `max_drawdown` (DECIMAL) - Maximum loss during scenario
- `recovery_time_months` (INTEGER) - Time to recover losses

### 8. scenario_probability_history
**Purpose**: Tracks changes in scenario probabilities over time
- `id` (Primary Key)
- `scenario_id` (Foreign Key) - Target scenario
- `date` (TIMESTAMP) - Probability update date
- `probability` (DECIMAL) - Updated probability value
- `reason` (TEXT) - Why probability changed
- `updated_by` (VARCHAR) - Who/what updated it

### 9. strategies
**Purpose**: Investment strategy definitions
- `id` (Primary Key)
- `name` (VARCHAR) - Strategy name
- `description` (TEXT) - Strategy details
- `strategy_type` (VARCHAR) - Type (Growth, Value, Momentum, etc.)
- `risk_level` (VARCHAR) - Conservative/Moderate/Aggressive
- `rebalance_frequency` (VARCHAR) - How often to rebalance
- `allocation_rules` (JSON) - Asset allocation rules

### 10. strategy_performance
**Purpose**: Historical performance metrics for strategies
- `id` (Primary Key)
- `strategy_id` (Foreign Key) - Target strategy
- `period_start` (DATE) - Performance period start
- `period_end` (DATE) - Performance period end
- `total_return` (DECIMAL) - Total return percentage
- `annualized_return` (DECIMAL) - Annualized return
- `volatility` (DECIMAL) - Return volatility
- `sharpe_ratio` (DECIMAL) - Risk-adjusted return
- `max_drawdown` (DECIMAL) - Maximum loss period

### 11. strategy_scenarios
**Purpose**: Links strategies to applicable scenarios
- `id` (Primary Key)
- `strategy_id` (Foreign Key) - Target strategy
- `scenario_id` (Foreign Key) - Applicable scenario
- `weight` (DECIMAL) - Scenario importance for this strategy
- `expected_performance` (DECIMAL) - Expected return in this scenario

### 12. trades
**Purpose**: Individual trade transactions
- `id` (Primary Key)
- `portfolio_id` (Foreign Key) - Portfolio making trade
- `ticker` (VARCHAR) - Stock symbol traded
- `trade_type` (VARCHAR) - BUY/SELL
- `shares` (DECIMAL) - Number of shares
- `price` (DECIMAL) - Execution price per share
- `trade_date` (TIMESTAMP) - Execution timestamp
- `commission` (DECIMAL) - Trading fees
- `reason` (TEXT) - Why trade was made
- `strategy_signal` (VARCHAR) - What triggered the trade

## Key Relationships

### Portfolio Management Flow
```
portfolios → positions → trades
portfolios → rebalancing_events
portfolios → strategy_scenarios
```

### Strategy & Performance Tracking
```
strategies → strategy_performance
strategies → strategy_scenarios → scenarios
strategies → portfolios
```

### Analysis & Decision Making
```
analysis_history → trades (analysis drives trading decisions)
news_events → analysis_history (news impacts analysis)
scenario_outcomes → rebalancing_events (stress tests trigger rebalancing)
```

### Risk Management
```
scenarios → scenario_outcomes → portfolio adjustments
scenario_probability_history → strategy adjustments
```

## Usage Patterns

### 1. Batch Analysis Storage
- Store comprehensive analysis results from NASDAQ, NYSE, ASX stock lists
- Track all 10+ analysis methods per stock (DCF, Technical, AI Insights, etc.)
- Maintain batch identifiers for bulk processing runs
- Store execution metrics and quality grades for performance monitoring

### 2. Portfolio Analysis
- Query `positions` and `analysis_history` to evaluate current holdings
- Use `news_events` to understand recent market impacts
- Check `scenario_outcomes` for stress test results
- Filter by exchange and company type for targeted analysis

### 3. Strategy Backtesting
- Use `strategy_performance` for historical results
- Apply `scenarios` to test strategy robustness
- Track `rebalancing_events` for strategy execution costs
- Leverage batch analysis results for universe selection

### 4. Risk Assessment
- Monitor `scenario_probability_history` for changing market conditions
- Analyze `scenario_outcomes` across different portfolios
- Use `news_events` sentiment for market timing
- Cross-reference quality grades with recommendation confidence

### 5. Performance Attribution
- Link `trades` to `analysis_history` to evaluate decision quality
- Compare `strategy_performance` across different approaches
- Track `rebalancing_events` impact on returns
- Analyze method-specific recommendation accuracy over time

### 6. Market Screening
- Query `analysis_history` by recommendation strength and confidence
- Filter by exchange, company type, and quality grade
- Identify bullish convergence across multiple analysis methods
- Track analyst alignment and deviation patterns

This schema supports comprehensive portfolio management with historical tracking, scenario analysis, and performance attribution capabilities. The `analysis_history` table serves as the central repository for all batch analysis results from major exchanges (NASDAQ, NYSE, ASX), storing comprehensive multi-method analysis with full recommendation breakdowns and quality assessments.