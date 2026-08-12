# Stock Analysis Framework - Complete Architecture Guide

## - DISCLAIMER

This is a personal project to analyse stocks for investment. The outputs of this project are not intended as investment advice. Carry out your own research for stock investments.

## Table of Contents
1. [System Overview](#system-overview)
2. [Quick Start](#quick-start)
3. [Architecture Components](#architecture-components)
4. [Analysis Flow](#analysis-flow)
5. [Data Models](#data-models)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)
8. [Deployment](#deployment)

---

## System Overview



## - What does this project do

The idea is to run basic quant analysis such as DCF, Technical against one or multiple stocks to derive a share price value. Compare the derived share value with value predicted by analysts on Yahoo Finance (available from yahoo finance api)

Where 1 or more of the quant analysis matches, the stock may be considered for further analysis.

*** NOT intended as investment advice ***

### Key Capabilities
- **Multi-method valuation**: DCF, Comparable, Technical, Startup-specific
- **AI-powered insights**: LLM analysis using OpenAI/Groq/xAI
- **Professional integration**: Analyst consensus and news sentiment
- **Batch processing**: Analyze 1000+ stocks in 10-15 minutes
- **Interactive dashboard**: Streamlit-based UI with real-time analysis

### Technology Stack
- **Backend**: Python 3.8+, FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **LLM Providers**: OpenAI (GPT-4), Groq (Llama-3), xAI (Grok)
- **Data Sources**: Yahoo Finance, SEC EDGAR
- **Frontend**: Streamlit
- **Processing**: Async/parallel execution with timeouts

---

## Quick Start

### 1. Installation
```bash
# Clone repository
git clone <repository-url>
cd finance-app

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_dashboard.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database URL
```

### 2. Database Setup
```bash
# Create database
python create_database.py

# Database will be created at:
# postgresql://user:password@localhost:5432/strategy_framework
```

### 3. Run Services
```bash
# Start API server (port 8000)
python run_api.py

# Start dashboard (port 8501)
python run_dashboard.py
```

### 4. First Analysis
```bash
# Analyze a single stock
curl -X POST http://localhost:8000/analyze/AAPL

# Or use the dashboard at http://localhost:8501
```

---

## Architecture Components

### 1. Analysis Orchestrator
**Location**: `src/share_insights_v1/services/orchestration/analysis_orchestrator.py`

**Purpose**: Central coordinator that manages all 14 analyzers

**Key Functions**:
- Company type classification (Mature/Growth/Startup/Financial)
- Analyzer selection based on company type
- Parallel execution with timeouts (60s overall, 30s per analyzer)
- Result aggregation and quality scoring

**Company Type Logic**:
```python
# Mature: Profitable, established, positive FCF
# Growth: Profitable, high growth, expanding
# Startup: Loss-making, early stage, high burn rate
# Financial: Banks, insurance, REITs (no DCF)
```

### 2. Specialized Analyzers (14 Total)

**Location**: `src/share_insights_v1/implementations/analyzers/`

#### Core Valuation Analyzers

**DCF Analyzer** (`dcf_analyzer.py`)
- Discounted Cash Flow valuation
- Free cash flow projections (5 years)
- WACC calculation (cost of equity + cost of debt)
- Terminal value (hybrid: perpetuity growth + EV/EBITDA multiple, averaged), with a
  configurable dominance cap so terminal value can't silently swamp the valuation
- Quality adjustments for data reliability
- **Scenario analysis**: every run computes a **Base Case** (the sector/quality-adjusted
  default, unchanged from a plain single-estimate DCF) plus four automatic alternative
  scenarios nested under `result['scenarios']`:
  - **Bull (High Growth)** - raises the growth-rate ceiling so a hypergrowth company's real
    historical CAGR flows through instead of being clamped by the sector default (still
    capped, at 75%, not literally unbounded)
  - **Bear** - tighter growth cap, lower terminal growth, and the terminal-value dominance
    cap actually engaged
  - **Rate Shock (+100bps)** - shifts the risk-free rate and market return together (holding
    the equity risk premium constant) to isolate Fed-move sensitivity without changing the
    growth assumptions
  - **Forward Guidance** - uses analyst next-year consensus growth (from yfinance's
    `earnings_estimate`/`revenue_estimate`) instead of historical CAGR - a genuinely
    different, forward-looking signal rather than just a different cap on the same
    backward-looking number. Revenue growth is used as the FCF growth proxy and EPS growth
    as the EBITDA growth proxy (yfinance has no direct forward FCF/EBITDA estimate). Falls
    back to the identical Base Case historical-CAGR calculation per metric when analyst
    coverage is thin (<2 analysts) or unavailable. The raw estimates (growth %, EPS/revenue
    estimate, analyst counts, long-term growth if covered) are surfaced in
    `dcf_calculations.forward_guidance` for display, independent of whether they were thin
    enough to trigger the fallback
  - Plus an optional **Custom** scenario if the caller supplies `data['dcf_overrides']`
    (max CAGR, terminal growth, terminal value ratio cap, EV/EBITDA exit multiple, risk-free
    rate) - used by the dashboard's "Custom Scenario" form via a dedicated lightweight
    endpoint (see API Layer) so exploring assumptions doesn't require re-running the full
    multi-analyzer pipeline
  - All scenarios reuse one fetched `yf.Ticker` per analysis rather than re-fetching per
    scenario; the Forward Guidance scenario's extra `earnings_estimate`/`revenue_estimate`
    lookups only happen when that scenario runs, not for every analysis
- **Applicable**: Mature/Growth companies only

**Comparable Analyzer** (`comparable_analyzer.py`)
- Peer company valuation
- Multiples: P/E, P/B, P/S, EV/EBITDA
- Sector-specific adjustments
- **Live peer data blending**: target multiples are blended with live peer-observed averages
  (`multiple_sources` reports which multiples were actually peer-blended vs. config-only
  fallback) rather than relying purely on static sector defaults
- **Region-aware peer selection**: peers are found via a live equity screener scoped to the
  target's own exchange/region (so ASX/NZX/etc. tickers get real regional peers instead of
  defaulting to US names) and sized to the target's own market-cap band, not just the
  largest company in the industry; peer valuation ratios are bounds-checked to filter out
  broken data from foreign ADR/OTC listings before they can skew the multiples
  - Falls back to a static peer table only if the live screener finds nothing
- **Peer comparison output**: `peer_averages` (raw peer figures), `relative_position`
  (Discount/Premium/Inline/Superior/Below per metric), and `peer_insights` (plain-English
  summary sentences)
- **Confidence** reflects how much of the valuation rests on real peer data vs. config-only
  defaults, rather than a fixed label
- **Applicable**: All company types

**Technical Analyzer** (`technical_analyzer.py`)
- Price pattern analysis
- Indicators: RSI, MACD, Bollinger Bands, Stochastic, ADX
- Support/resistance levels (swing points, volume profile)
- Fibonacci retracements
- Trend identification (uptrend/downtrend/sideways)
- **Applicable**: All company types

**Startup Analyzer** (`startup_analyzer.py`)
- Early-stage company analysis
- Growth metrics (revenue growth, user growth)
- Burn rate and runway calculation
- Funding rounds and valuation
- **Applicable**: Loss-making companies only

#### Professional Integration Analyzers

**Analyst Consensus Analyzer** (`analyst_consensus_analyzer.py`)
- Professional analyst price targets
- Consensus recommendations (Buy/Hold/Sell)
- Analyst count and coverage
- Target price range (high/low/mean)
- **Data Source**: Yahoo Finance

**News Sentiment Analyzer** (`news_sentiment_analyzer.py`)
- Real-time news sentiment analysis
- Fact extraction for thesis generation
- Sentiment scoring (positive/negative/neutral)
- Event detection (earnings, M&A, regulatory)
- **Note**: Does NOT contribute to weighted recommendation
- **Data Source**: Yahoo Finance (yfinance API)

#### Business Analysis Analyzers

**AI Insights Analyzer** (`ai_insights_analyzer.py`)
- LLM-powered business analysis
- Combines financial metrics, market position, growth prospects
- Generates qualitative insights
- **LLM Providers**: Groq (primary), OpenAI (fallback), xAI (fallback)

**Business Model Analyzer** (`business_model_analyzer.py`)
- Revenue model analysis
- Cost structure evaluation
- Business sustainability assessment
- Competitive moat identification

**Competitive Position Analyzer** (`competitive_position_analyzer.py`)
- Market share analysis
- Competitive advantages
- Porter's Five Forces analysis
- Industry positioning

**Management Quality Analyzer** (`management_quality_analyzer.py`)
- Leadership assessment
- Governance structure evaluation
- Insider ownership analysis
- Management track record

**Financial Health Analyzer** (`financial_health_analyzer.py`)
- Balance sheet strength
- Liquidity ratios (current ratio, quick ratio)
- Solvency analysis (debt/equity, interest coverage)
- **Data Source**: SEC EDGAR (US companies only)

**Revenue Stream Analyzer** (`revenue_stream_analyzer.py`)
- Revenue diversification analysis
- Segment breakdown
- Growth driver identification
- Geographic revenue distribution

**Industry Analysis Analyzer** (`industry_analysis_analyzer.py`)
- Sector trends analysis
- Market dynamics evaluation
- Competitive landscape overview
- Industry growth prospects

**Peer Comparison Analyzer** (`peer_comparison_analyzer.py`)
- Direct peer benchmarking
- Financial metrics comparison
- Operational metrics comparison
- Relative valuation

### 3. Recommendation Service
**Location**: `src/share_insights_v1/services/recommendation/recommendation_service.py`

**Purpose**: Consolidates analyzer results into final recommendation

**Analyzer Weights**:
```python
{
    'dcf': 0.25,              # 25% - Intrinsic value
    'comparable': 0.2,        # 20% - Relative valuation
    'technical': 0.15,        # 15% - Market sentiment
    'startup': 0.4,           # 40% - For loss-making companies
    'analyst_consensus': 0.25, # 25% - Professional opinion
    'ai_insights': 0.15       # 15% - Qualitative analysis
}
```

**Recommendation Scoring**:
- Strong Buy: +2
- Buy: +1
- Hold: 0
- Sell: -1
- Strong Sell: -2

**Final Recommendation Logic**:
```python
consensus_score = Σ(analyzer_score × weight) / total_weight

if consensus_score >= 1.5:  → Strong Buy
elif consensus_score >= 0.5: → Buy
elif consensus_score <= -1.5: → Strong Sell
elif consensus_score <= -0.5: → Sell
else: → Hold
```

**Confidence Level**:
- High: ≥3 analyses AND |consensus_score| ≥ 1.0
- Medium: ≥2 analyses AND |consensus_score| ≥ 0.5
- Low: Otherwise

**Target Price Calculation**:
```python
# Weighted average of valid price targets
target_price = Σ(analyzer_price × weight) / total_valid_weight

# Excludes: zero, null, or invalid prices
# Auto-normalizes weights based on available prices
```

### 4. API Layer
**Location**: `src/share_insights_v1/api/`

**Framework**: FastAPI with async processing

**Key Endpoints**:
```python
POST /analyze/{ticker}              # Single stock analysis (all analyzers)
POST /analyze/{ticker}/dcf-scenario # Single custom DCF scenario only - fast,
                                     # no other analyzers, no LLM calls, no DB writes
POST /batch/upload                  # Batch CSV upload
GET /batch/{job_id}/status          # Job status
GET /batch/{job_id}/results         # Job results
GET /health                         # Health check
```

**Response Format**:
```json
{
  "ticker": "AAPL",
  "final_recommendation": {
    "recommendation": "Buy",
    "consensus_score": 1.05,
    "target_price": 183.25,
    "confidence": "High",
    "risk_level": "Medium"
  },
  "analyses": {
    "dcf": {...},
    "technical": {...},
    "comparable": {...}
  }
}
```

### 5. Batch Processing System

**Batch Analysis Service** (`services/batch/batch_analysis_service.py`)
- High-volume direct processing
- Processes 1000+ stocks in 10-15 minutes
- Incremental CSV writing
- Memory efficient

**Batch Comparison Service** (`services/comparison/batch_comparison_service.py`)
- Multi-method analyst alignment analysis
- Categorizes stocks: Investment_Aligned, Precise_Aligned, Moderate_Aligned, Divergent
- Performance metrics per method

**Bullish Convergence Service** (`services/comparison/bullish_convergence_service.py`)
- Cross-method convergence identification
- Identifies high-conviction opportunities
- Filters for multi-method agreement

### 6. Interactive Dashboard
**Location**: `src/share_insights_v1/dashboard/`

**Framework**: Streamlit

**Pages**:
- **Batch Results**: Overview with filtering
- **Detailed Analysis**: Individual stock deep-dive
- **Analyst Alignment**: Method performance analysis
- **Bullish Convergence**: Multi-method agreement
- **Watchlist**: Custom stock lists
- **Thesis Generation**: Professional investment theses

**Features**:
- Interactive filtering
- Real-time API integration
- Modal dialogs with maximize/restore
- SVG price charts
- Financial charts (revenue, income, cash flow)

### 7. Database Layer
**Location**: `src/share_insights_v1/services/database/`

**Database**: PostgreSQL

**Key Tables**:
- `analysis_history`: Comprehensive analysis results
- `batch_jobs`: Batch processing jobs
- `portfolios`: User portfolios
- `positions`: Portfolio positions
- `trades`: Trade history
- `scenarios`: Scenario analysis

**Storage Flow**:
```
Analysis → AnalysisStorageService → DatabaseService → PostgreSQL
```

**Configuration**:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/strategy_framework
```

### 8. LLM Provider System
**Location**: `src/share_insights_v1/implementations/llm_providers/`

**Providers**:
- **Groq** (Primary): Llama-3.3, Mixtral-8x7b - Fast and cost-effective
- **OpenAI** (Fallback): GPT-4, GPT-4o-mini - High quality
- **xAI** (Fallback): Grok-beta - Alternative provider

**Configuration**: `config/llm_config.yaml`

**Fallback Chain**:
```
Groq → OpenAI → xAI → Error
```

**Usage Points**:
- AI Insights Analyzer
- News Sentiment Analyzer
- Thesis Generation
- Business Model Analysis

---

## Analysis Flow

### Single Stock Analysis Flow

```
1. API Request (POST /analyze/AAPL)
   ↓
2. Analysis Orchestrator
   ├─ Classify company type (Mature/Growth/Startup/Financial)
   ├─ Select applicable analyzers
   └─ Execute analyzers in parallel (60s timeout)
   ↓
3. Individual Analyzers (30s timeout each)
   ├─ DCF Analyzer → Fair value calculation
   ├─ Technical Analyzer → Price patterns & indicators
   ├─ Comparable Analyzer → Peer valuation
   ├─ Analyst Consensus → Professional targets
   ├─ AI Insights → LLM analysis
   └─ Other analyzers → Additional insights
   ↓
4. Recommendation Service
   ├─ Calculate weighted consensus score
   ├─ Determine final recommendation
   ├─ Calculate target price
   └─ Assess confidence & risk
   ↓
5. Storage (if enabled)
   ├─ AnalysisStorageService
   └─ DatabaseService → PostgreSQL
   ↓
6. API Response
   └─ JSON with final recommendation + all analyses
```

### Batch Analysis Flow

```
1. CSV Upload (tickers list)
   ↓
2. Batch Analysis Service
   ├─ Create batch job
   ├─ Process stocks in parallel
   └─ Incremental CSV writing
   ↓
3. For each stock:
   ├─ Run analysis orchestrator
   ├─ Get final recommendation
   └─ Write to output CSV
   ↓
4. Batch Comparison (optional)
   ├─ Compare methods vs analyst consensus
   ├─ Categorize alignment
   └─ Generate performance metrics
   ↓
5. Bullish Convergence (optional)
   ├─ Identify multi-method agreement
   ├─ Filter high-conviction stocks
   └─ Generate convergence report
   ↓
6. Dashboard Display
   └─ Interactive results exploration
```

---

## Data Models

### ComprehensiveAnalysisResult
```python
{
    "ticker": str,
    "company_type": str,  # Mature/Growth/Startup/Financial
    "current_price": float,
    "final_recommendation": {
        "recommendation": str,  # Strong Buy/Buy/Hold/Sell/Strong Sell
        "consensus_score": float,
        "target_price": float,
        "confidence": str,  # High/Medium/Low
        "risk_level": str   # High/Medium/Low
    },
    "analyses": {
        "dcf": {...},
        "technical": {...},
        "comparable": {...},
        # ... other analyzers
    },
    "financial_metrics": {...},
    "quality_grade": str  # A/B/C/D/F
}
```

### AnalyzerResult
```python
{
    "recommendation": str,
    "predicted_price": float,
    "confidence": float,
    "reasoning": str,
    "key_metrics": dict,
    "risks": list,
    "opportunities": list
}
```

---

## API Reference

### Single Stock Analysis
```bash
POST /analyze/{ticker}

Response:
{
  "ticker": "AAPL",
  "status": "success",
  "data": ComprehensiveAnalysisResult
}
```

### Custom DCF Scenario
```bash
POST /analyze/{ticker}/dcf-scenario
Content-Type: application/json

Body (all fields optional - omitted fields fall back to the ticker's normal
sector/quality-adjusted Base Case values):
{
  "max_cagr_threshold": 0.30,
  "default_terminal_growth": 0.03,
  "max_terminal_value_ratio": 0.85,
  "default_ev_ebitda_multiple": 15.0,
  "risk_free_rate_override": 0.05
}

Response:
{
  "ticker": "AAPL",
  "scenario": { ...same shape as one entry in analyses.dcf.scenarios... }
}
```
Runs only `DCFAnalyzer` (no other analyzers, no LLM calls, no DB writes) so it's fast
enough for interactive what-if exploration from the dashboard's DCF tab.

### Batch Analysis
```bash
# Upload CSV
POST /batch/upload
Content-Type: multipart/form-data
File: tickers.csv (format: Symbol,Security Name)

Response:
{
  "job_id": "uuid",
  "status": "processing",
  "total_stocks": 100
}

# Check Status
GET /batch/{job_id}/status

Response:
{
  "job_id": "uuid",
  "status": "completed",
  "progress": 100,
  "completed": 100,
  "total": 100
}

# Get Results
GET /batch/{job_id}/results

Response:
{
  "job_id": "uuid",
  "results": [ComprehensiveAnalysisResult, ...]
}
```

---

## Configuration

### Environment Variables (.env)
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/strategy_framework

# LLM Providers (at least one required)
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key
XAI_API_KEY=your_xai_key

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/ui.log

# AWS (optional)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### LLM Configuration (config/llm_config.yaml)
```yaml
providers:
  - name: groq
    enabled: true
    priority: 1
    models:
      - llama-3.3-70b-versatile
      - mixtral-8x7b-32768
  
  - name: openai
    enabled: true
    priority: 2
    models:
      - gpt-4o-mini
      - gpt-4
  
  - name: xai
    enabled: true
    priority: 3
    models:
      - grok-beta
```

---

## Deployment

### Local Development
```bash
# Start services
python run_api.py &
python run_dashboard.py &

# Access
API: http://localhost:8000
Dashboard: http://localhost:8501
```

### Production (AWS EC2)
```bash
# Recommended instance: t3.medium (4GB RAM)
# t3.micro (1.8GB) insufficient for batch processing

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with production credentials

# Run with process manager
nohup python run_api.py > api.log 2>&1 &
nohup python run_dashboard.py > dashboard.log 2>&1 &

# Or use systemd services
sudo systemctl start stock-analysis-api
sudo systemctl start stock-analysis-dashboard
```

### Database Setup (PostgreSQL)
```bash
# Install PostgreSQL
sudo apt-get install postgresql

# Create database
python create_database.py

# Run migrations (if needed)
python migrate_investment_theses.py
```

### Security Considerations
- Use environment variables for all credentials
- Enable HTTPS for production API
- Implement rate limiting
- Use VPC security groups on AWS
- Enable CloudWatch logging
- Rotate API keys regularly

---

## Performance Characteristics

- **Single Stock**: 2-5 seconds
- **Batch (1000 stocks)**: 10-15 minutes
- **Memory**: ~500MB per analysis process
- **Database**: ~1MB per comprehensive analysis
- **API Throughput**: 10-20 requests/second

---

## Known Limitations

1. **News Data Freshness**: yfinance may return stale news for small-cap stocks
2. **SEC EDGAR**: Only available for US companies
3. **DCF Limitations**: Not applicable for financial companies or loss-making startups.
   The Base Case's growth-rate cap is sector/quality-adjusted, not company-specific, so it
   can still understate genuine hypergrowth names - the automatic "Bull (High Growth)"
   scenario and the Custom-scenario endpoint exist specifically to surface what the model
   implies without that cap
4. **LLM Costs**: API calls incur costs (use Groq for cost-effectiveness)
5. **Rate Limits**: Yahoo Finance and LLM providers have rate limits

---

## Troubleshooting

### Common Issues

**"All LLM providers failed"**
- Check API keys in .env
- Verify internet connectivity
- Check provider status pages

**"Database connection failed"**
- Verify DATABASE_URL in .env
- Check PostgreSQL is running
- Verify credentials

**"Analysis timeout"**
- Increase timeout in orchestrator
- Check network connectivity
- Verify data provider availability

**"Memory issues on EC2"**
- Upgrade to t3.medium or larger
- Add swap space
- Reduce batch size

---

## Support & Contributing

- **Issues**: Report bugs via GitHub Issues
- **Security**: See SECURITY.md for vulnerability reporting
- **Contributing**: See CONTRIBUTING.md for guidelines
- **Documentation**: This file is the single source of truth

---

**Last Updated**: 2026-08-11
**Version**: 1.0
