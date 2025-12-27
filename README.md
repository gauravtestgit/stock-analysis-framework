# Stock Analysis Framework

A comprehensive stock analysis framework with multiple valuation methods, analyst alignment analysis, and interactive dashboard for investment decision making.

## Architecture Overview

### Core Components

#### 1. Analysis Orchestrator
- **Location**: `src/share_insights_v1/services/orchestration/analysis_orchestrator.py`
- **Purpose**: Central orchestrator managing 8+ specialized analyzers
- **Features**: Company type classification, analyzer registration, consensus scoring

#### 2. Specialized Analyzers
- **Fundamental Analysis**: Most comprehensive approach examining financial statements, key ratios (P/E, debt-to-equity, ROE), competitive position, management quality, and industry trends with financial modeling for intrinsic value estimation
- **Technical Analysis**: Price pattern and trading data analysis using charts, support/resistance levels, moving averages, RSI indicators, and volume analysis to predict future movements based on historical patterns
- **Valuation Analysis**: Intrinsic worth calculation using DCF models, comparable company analysis, and precedent transaction analysis to determine overvaluation/undervaluation relative to fair value
- **Industry & Competitive Analysis**: Market context evaluation including size/growth rates, competitive dynamics (Porter's Five Forces), regulatory environment, and technological disruption assessment
- **Qualitative Analysis**: Non-quantifiable factor assessment including management track record, corporate governance, brand strength, litigation risks, and reputational considerations
- **Event-Driven Analysis**: Catalyst-focused evaluation of earnings releases, M&A activity, product launches, and regulatory decisions with significant price impact potential
- **AI Insights**: LLM-powered business analysis combining multiple data sources for comprehensive assessment
- **News Sentiment**: Real-time news impact assessment on stock recommendations

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
- **Database**: PostgreSQL (`postgresql://postgres:M3rcury1@localhost:5432/strategy_framework`)
- **ORM**: SQLAlchemy with declarative models
- **Tables**: `analysis_history`, `portfolios`, `positions`, `trades`, `scenarios`, etc.

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
- **Providers**: OpenAI, Anthropic, Groq, Ollama support
- **Configuration**: Environment-based provider selection with fallback chain
- **Models**: GPT-4, Claude-3, Llama-3, Mixtral support

#### 2. LLM Data Flow Architecture
```
Stock Analysis Request → LLM Provider Factory → Selected Provider → Model API
                                ↓
                        Prompt Templates → Context Assembly → Response Processing
                                ↓
                        Analysis Results → JSON Serialization → Dashboard Display
```

#### 3. LLM Provider Configuration
```python
# Environment Variables Required
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GROQ_API_KEY=your_groq_key

# Provider Selection (automatic fallback)
# 1. OpenAI GPT-4 (primary)
# 2. Anthropic Claude-3 (fallback)
# 3. Groq Mixtral (fallback)
# 4. Ollama Local (fallback)
```

#### 4. LLM Integration Points
- **AI Insights Analyzer**: `src/share_insights_v1/services/analyzers/ai_insights_analyzer.py`
- **News Sentiment Analyzer**: Real-time news analysis with LLM processing
- **Thesis Generation**: Professional investment thesis creation
- **Qualitative Analysis**: Management and governance assessment

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
# Create .env file with LLM provider keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GROQ_API_KEY=your_groq_api_key_here

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
│   ├── llm_providers/      # LLM provider implementations
│   │   ├── openai_provider.py      # OpenAI GPT integration
│   │   ├── anthropic_provider.py   # Anthropic Claude integration
│   │   ├── groq_provider.py        # Groq Mixtral integration
│   │   └── ollama_provider.py      # Local Ollama integration
│   └── data_providers/
│       └── yahoo_provider.py       # Yahoo Finance data (with JSON serialization fixes)
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