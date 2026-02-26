# Stock Analysis Framework

A comprehensive stock analysis framework with multiple valuation methods, analyst alignment analysis, and interactive dashboard for investment decision making.

## Architecture Overview

### Core Components

#### 1. Analysis Orchestrator
- **Location**: `src/share_insights_v1/services/orchestration/analysis_orchestrator.py`
- **Purpose**: Central orchestrator managing 14 specialized analyzers
- **Features**: Company type classification, analyzer registration, consensus scoring

#### 2. Specialized Analyzers (14 Total)
- **Location**: `src/share_insights_v1/implementations/analyzers/`
- **DCF Analyzer**: Discounted Cash Flow valuation with free cash flow projections, WACC calculation, and terminal value estimation
- **Comparable Analyzer**: Peer company valuation using P/E, P/B, P/S multiples with sector-specific adjustments
- **Technical Analyzer**: Price pattern analysis with RSI, MACD, Bollinger Bands, Stochastic, ADX indicators and trend identification
- **AI Insights Analyzer**: LLM-powered business analysis combining financial metrics, market position, and growth prospects
- **News Sentiment Analyzer**: Real-time news sentiment analysis with enhanced fact extraction for thesis generation
- **Business Model Analyzer**: Revenue model, cost structure, and business sustainability assessment
- **Competitive Position Analyzer**: Market share, competitive advantages, and Porter's Five Forces analysis
- **Management Quality Analyzer**: Leadership assessment, governance structure, and insider ownership evaluation
- **Financial Health Analyzer**: Balance sheet strength, liquidity ratios, and solvency analysis using SEC EDGAR data
- **Analyst Consensus Analyzer**: Professional analyst price targets, recommendations, and consensus ratings
- **Revenue Stream Analyzer**: Revenue diversification, segment analysis, and growth driver identification
- **Industry Analysis Analyzer**: Sector trends, market dynamics, and competitive landscape evaluation
- **Startup Analyzer**: Early-stage company analysis focusing on growth metrics and burn rate
- **Peer Comparison Analyzer**: Direct peer benchmarking across financial and operational metrics

#### 3. API Layer
- **Location**: `src/share_insights_v1/api/`
- **Framework**: FastAPI with async processing
- **Endpoints**: Single stock analysis, batch processing, configuration
- **Features**: Background job management, CSV upload/download

#### 4. Batch Processing System
- **Batch Analysis Service**: High-volume direct processing
- **Batch Comparison Service**: Multi-method analyst alignment analysis
- **Bullish Convergence Service**: Cross-method convergence identification
- **Performance**: Services layer significantly faster than API for bulk processing

#### 5. Interactive Dashboard
- **Framework**: Streamlit with enhanced UI components
- **Pages**: Batch results, detailed analysis, analyst alignment, bullish convergence, thesis generation
- **Features**: Interactive filtering, watchlist management, real-time API integration, modal dialogs, SVG price charts

#### 6. Professional Thesis Generation
- **Location**: `src/share_insights_v1/dashboard/pages/thesis_generation_full.py`
- **Purpose**: Generate professional-grade investment theses using LLM analysis
- **Features**: Bull case, bear case, and balanced thesis generation with Seeking Alpha quality standards

### Data Flow Architecture

```
Stock Lists (CSV) → Batch Analysis → Method Comparison → Convergence Analysis → Dashboard/API
                         ↓
                  Database Storage
                         ↓
                  PostgreSQL Database
```

## Database Storage Flow

### Database Architecture
- **Database**: PostgreSQL (configure via `DATABASE_URL` environment variable)
- **ORM**: SQLAlchemy with declarative models
- **Tables**: `analysis_history`, `portfolios`, `positions`, `trades`, `scenarios`, etc.
- **Example**: `postgresql://user:password@localhost:5432/strategy_framework`

### Storage Flow
1. **Analysis Execution**:
   - `AnalysisOrchestrator` → Individual analyzers → Analysis results
   
2. **Database Storage**:
   - `AnalysisStorageService` → `DatabaseService` → PostgreSQL `analysis_history` table
   
3. **Storage Triggers**:
   - **Batch Analysis**: `BatchAnalysisService(save_to_db=True)` 
   - **API Calls**: Dashboard → API endpoints → Storage service
   - **Test Scripts**: Manual execution with storage enabled

### Key Storage Components
- **AnalysisStorageService**: `src/share_insights_v1/services/storage/analysis_storage_service.py`
- **DatabaseService**: `src/share_insights_v1/services/database/database_service.py`
- **Database Models**: `src/share_insights_v1/models/database.py` & `strategy_models.py`
- **Analysis History Table**: Stores comprehensive analysis results with individual method breakdowns

### Storage Configuration
```python
# Enable database storage in batch analysis
batch_service = BatchAnalysisService(save_to_db=True)

# Storage happens automatically via:
# 1. AnalysisStorageService.store_comprehensive_analysis()
# 2. DatabaseService.save_comprehensive_analysis()
# 3. PostgreSQL analysis_history table
```

## LLM Provider Integration

### LLM Configuration & Data Flow

#### 1. LLM Provider Setup
- **Location**: `src/share_insights_v1/implementations/llm_providers/`
- **Providers**: OpenAI (GPT-4), Groq (Llama-3, Mixtral), xAI (Grok)
- **Configuration**: YAML-based provider selection (`config/llm_config.yaml`) with automatic fallback
- **Models**: GPT-4, GPT-4o-mini, Llama-3.1, Llama-3.3, Mixtral-8x7b, Grok-beta

#### 2. LLM Data Flow Architecture
```
Stock Analysis Request → LLM Provider Factory → Selected Provider → Model API
                                ↓
                        Prompt Templates → Context Assembly → Response Processing
                                ↓
                        Analysis Results → JSON Serialization → Dashboard Display
```

#### 3. LLM Provider Configuration
```bash
# Environment Variables Required (set in .env file)
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
XAI_API_KEY=your_xai_key

# Provider Selection (automatic fallback via llm_config.yaml)
# 1. Groq Llama-3.3 (primary - fast and cost-effective)
# 2. OpenAI GPT-4o-mini (fallback)
# 3. xAI Grok-beta (fallback)
# Configuration managed in: src/share_insights_v1/config/llm_config.yaml
```

#### 4. LLM Integration Points
- **AI Insights Analyzer**: `src/share_insights_v1/implementations/analyzers/ai_insights_analyzer.py`
- **News Sentiment Analyzer**: `src/share_insights_v1/implementations/analyzers/news_sentiment_analyzer.py`
- **Thesis Generation**: `src/share_insights_v1/dashboard/pages/thesis_generation_full.py`
- **Business Model Analysis**: LLM-powered business model evaluation
- **Management Quality**: LLM-assisted governance and leadership assessment

### Recent Financial Data Fixes (December 2024)

#### 1. JSON Serialization Fix
- **Issue**: Pandas Timestamp objects causing TypeError in JSON serialization
- **Fix**: Modified `yahoo_provider.py` serialize_dataframe function to convert Timestamps to strings
- **Impact**: Resolved API crashes when returning financial data

#### 2. Financial Display Fix
- **Issue**: $0 values showing in financial info cards due to data structure changes
- **Fix**: Updated extraction logic in `thesis_generation_full.py` to handle serialized data format
- **Structure**: Changed from field->date->value to date->field->value format

#### 3. Chart Restoration & Enhancement
- **Added**: Financial charts modal with revenue, income, and cash flow trends
- **Fixed**: Syntax errors in chart generation (incomplete try statements, invalid f-string formats)
- **Enhanced**: Chronological ordering (oldest to newest) using reversed() function
- **Charts**: Blue revenue bars, yellow/green/red income bars, multi-color cash flow bars

#### 4. Modal Enhancement
- **Added**: Maximize/restore functionality for all analysis modals
- **Enhanced**: Better responsive design with proper scaling
- **Fixed**: JavaScript modal management with unique IDs per ticker

## Setup and Installation

### Prerequisites
- Python 3.8+
- Required packages: `pip install -r requirements.txt`
- Dashboard packages: `pip install -r requirements_dashboard.txt`
- **LLM API Keys**: At least one of OpenAI, Anthropic, or Groq API keys

### Environment Configuration
```bash
# Copy .env.example to .env and configure:
cp .env.example .env

# Required: Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/strategy_framework

# Required: At least one LLM provider API key
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here
XAI_API_KEY=your_xai_api_key_here

# Optional: Ollama for local LLM (no API key needed)
# Install Ollama and pull models: ollama pull llama3
```

### API Server
```bash
python run_api.py
```
- Server: http://localhost:8000
- Documentation: http://localhost:8000/docs
- **LLM Status**: Check `/health` endpoint for provider availability

### Dashboard
```bash
python run_dashboard.py
```
- Dashboard: http://localhost:8501
- **Financial Charts**: Available in thesis generation page with modal dialogs

## Analysis Workflow

### Step 1: Batch Analysis
Run comprehensive analysis on stock lists using either services or API:

**Option A: Direct Service (Faster)**
```bash
python src/share_insights_v1/tests/test_batch_analysis.py
```

**Option B: API (Background Processing)**
```bash
python src/share_insights_v1/tests/test_batch_api.py
```

**Input Files:**
- `nasdaq.csv` - NASDAQ listed stocks
- `nyse.csv` - NYSE listed stocks  
- `asx.csv` - ASX listed stocks

**Output:** `batch_analysis_YYYYMMDD_HHMMSS.csv` with comprehensive analysis results

### Step 2: Method Comparison Analysis
Compare valuation methods against professional analyst consensus:

```bash
python src/share_insights_v1/tests/test_batch_comparison.py
```

**Input:** Batch analysis CSV from Step 1
**Output:** 
- Method-specific files: `dcf_aligned.csv`, `technical_divergent.csv`, etc.
- Summary report: `analyst_alignment_YYYYMMDD_HHMMSS_report.txt`

### Step 3: Bullish Convergence Analysis
Identify stocks where multiple methods agree on bullish outlook:

```bash
python src/share_insights_v1/tests/test_bullish_convergence.py
```

**Input:** Method-specific files from Step 2
**Output:** 
- `bullish_convergent_consolidated.csv` - Cross-method convergence analysis
- `bullish_convergent_report.txt` - Summary insights

### Step 4: Interactive Analysis
Use dashboard or API for deeper analysis:

**Dashboard Features:**
- **Batch Results**: Overview of all analyzed stocks with filtering
- **Detailed Analysis**: Individual stock deep-dive with AI insights
- **Analyst Alignment**: Method performance and alignment analysis  
- **Bullish Convergence**: Multi-method agreement identification
- **Watchlist**: Build and analyze custom stock lists
- **Thesis Generation**: Professional investment thesis creation with bull/bear/balanced perspectives
- **Enhanced UI**: Modal dialogs, interactive SVG price charts, maximize/restore functionality

**API Endpoints:**
- `POST /analyze/{ticker}` - Single stock comprehensive analysis
- `POST /batch/upload` - Batch analysis via CSV upload
- `GET /batch/{job_id}/status` - Monitor batch job progress
- `GET /batch/{job_id}/results` - Retrieve batch results

## Key Features

### Multi-Method Valuation
- **6 Core Analysis Methods**: Fundamental, Technical, Valuation, Industry/Competitive, Qualitative, Event-Driven
- **Consensus Scoring**: Weighted recommendations across methods with statistical confidence intervals
- **Quality Adjustment**: Analysis confidence based on data completeness and reliability metrics
- **Cross-Validation**: Multiple method convergence analysis for high-conviction identification

### Analyst Alignment Analysis
- **Alignment Categories**: Investment_Aligned, Precise_Aligned, Moderate_Aligned, Divergent
- **Performance Metrics**: Method-specific alignment rates and deviation scores
- **Bullish Convergence**: Identification of high-conviction opportunities

### Interactive Dashboard
- **Real-time Filtering**: Dynamic analysis based on user criteria
- **Watchlist Management**: Build and analyze custom stock portfolios
- **Batch Processing**: Analyze entire watchlists with progress tracking
- **Visual Analytics**: Interactive SVG price charts and metrics for quick decision making
- **Enhanced Modals**: Maximize/restore functionality with detailed analysis views
- **Horizontal Card Layout**: Streamlined analysis display with expandable details

### Professional Thesis Generation
- **LLM-Powered Analysis**: Advanced prompts generating Seeking Alpha quality investment theses
- **Multiple Perspectives**: Bull case, bear case, and balanced investment analysis
- **Structured Format**: Professional sections including Investment Thesis Summary, Business Overview, Financial Analysis, Valuation Assessment, and Risk Analysis
- **Actionable Insights**: Clear investment recommendations with supporting rationale
- **Financial Charts**: Interactive revenue, income, and cash flow trend visualization
- **Enhanced Modals**: Maximize/restore functionality with comprehensive financial data display

### Professional Integration
- **Analyst Consensus**: Integration with professional analyst targets
- **News Sentiment**: Real-time news impact on stock recommendations
- **Quality Scoring**: Data quality assessment and confidence intervals

## File Structure

```
src/share_insights_v1/
├── api/                    # FastAPI endpoints and services
├── services/
│   ├── orchestration/      # Main analysis orchestrator
│   ├── analyzers/          # Individual analysis methods (including AI insights)
│   └── batch/              # Batch processing services
├── implementations/
│   ├── analyzers/          # 14 specialized analyzers
│   │   ├── dcf_analyzer.py
│   │   ├── comparable_analyzer.py
│   │   ├── technical_analyzer.py
│   │   ├── ai_insights_analyzer.py
│   │   ├── news_sentiment_analyzer.py
│   │   ├── business_model_analyzer.py
│   │   ├── competitive_position_analyzer.py
│   │   ├── management_quality_analyzer.py
│   │   ├── financial_health_analyzer.py
│   │   ├── analyst_consensus_analyzer.py
│   │   ├── revenue_stream_analyzer.py
│   │   ├── industry_analysis_analyzer.py
│   │   ├── startup_analyzer.py
│   │   └── peer_comparison_analyzer.py
│   ├── llm_providers/      # LLM provider implementations
│   │   ├── openai_provider.py      # OpenAI GPT integration
│   │   ├── groq_provider.py        # Groq Llama/Mixtral integration
│   │   ├── xai_provider.py         # xAI Grok integration
│   │   └── llm_manager.py          # Provider management and fallback
│   └── data_providers/
│       ├── yahoo_provider.py       # Yahoo Finance data (with JSON serialization fixes)
│       ├── sec_edgar_provider.py   # SEC EDGAR financial data
│       └── yahoo_peer_provider.py  # Peer comparison data
├── dashboard/              # Streamlit dashboard components
│   └── pages/
│       ├── thesis_generation_full.py  # Professional thesis generation (with financial charts)
│       └── ...             # Other dashboard pages
├── models/                 # Data models and schemas
├── resources/              # Input data and analysis outputs
└── tests/                  # Test scripts and validation
```

## Performance Characteristics

- **Single Stock Analysis**: 2-5 seconds per stock
- **Batch Processing**: 1000+ stocks in 10-15 minutes (services)
- **API Processing**: Background jobs with status tracking
- **Memory Efficiency**: Incremental CSV writing for large datasets
- **Scalability**: Horizontal scaling via multiple API instances

## Output Formats

### Analysis Results
- **CSV Format**: Structured data for further analysis
- **JSON API**: Real-time programmatic access
- **Interactive Dashboard**: Visual exploration and filtering

### Key Metrics
- **Price Targets**: Method-specific fair value estimates
- **Recommendations**: Buy/Hold/Sell with confidence scores
- **Alignment Scores**: Agreement with professional analysts
- **Quality Grades**: Data reliability and analysis confidence

## Known Limitations

### News Data Freshness (yfinance API)
- **Issue**: For small-cap stocks, yfinance may return stale/cached news that doesn't match Yahoo Finance website
- **Cause**: yfinance library uses a different API endpoint than the website with slower update cycles
- **Impact**: Small-cap stocks may show news from weeks/months ago instead of latest articles
- **Workaround**: None available - this is a yfinance library limitation
- **Note**: Large-cap stocks (AAPL, MSFT, etc.) typically have fresher news data

## Recent Updates & Fixes (December 2024)

### LLM Provider Integration
- **Multi-Provider Support**: OpenAI, Anthropic, Groq, and Ollama with automatic fallback
- **Environment Configuration**: Secure API key management with .env support
- **Provider Factory Pattern**: Centralized LLM provider management and selection
- **Error Handling**: Robust fallback chain for provider failures

### Financial Data & Visualization
- **JSON Serialization**: Fixed Pandas Timestamp serialization errors in Yahoo Finance provider
- **Data Structure**: Updated financial data extraction to handle serialized format (date->field->value)
- **Interactive Charts**: Added revenue, income, and cash flow trend visualization in modals
- **Chart Ordering**: Chronological display (oldest to newest) for better trend analysis
- **Modal Enhancement**: Maximize/restore functionality for detailed financial analysis

### Dashboard Improvements
- **Syntax Fixes**: Resolved incomplete try statements and invalid f-string format specifiers
- **Responsive Design**: Better modal scaling and layout management
- **Financial Cards**: Enhanced display with proper data extraction and error handling
- **Chart Legends**: Color-coded legends for income and cash flow chart interpretation

### Technical Debt Resolution
- **Error Handling**: Comprehensive exception handling in financial data processing
- **Code Quality**: Fixed syntax errors and improved code maintainability
- **Data Validation**: Better handling of missing or malformed financial data
- **Performance**: Optimized chart generation and modal rendering

This framework provides end-to-end stock analysis capabilities from bulk processing to detailed individual analysis, with professional-grade alignment validation, LLM-powered insights, and interactive exploration tools.