# Stock Analysis Framework

A comprehensive stock analysis framework with multiple valuation methods, analyst alignment analysis, and interactive dashboard for investment decision making.

## Architecture Overview

### Core Components

#### 1. Analysis Orchestrator
- **Location**: `src/share_insights_v1/services/orchestration/analysis_orchestrator.py`
- **Purpose**: Central orchestrator managing 8+ specialized analyzers
- **Features**: Company type classification, analyzer registration, consensus scoring

#### 2. Specialized Analyzers
- **DCF Analysis**: Discounted Cash Flow valuation
- **Technical Analysis**: Price patterns, moving averages, RSI
- **Comparable Company**: Industry multiple-based valuation
- **Startup Valuation**: Early-stage company analysis
- **AI Insights**: LLM-powered business analysis
- **News Sentiment**: Real-time news impact assessment
- **Business Model**: Revenue quality and scalability analysis
- **Financial Health**: Balance sheet and cash flow analysis

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
- **Framework**: Streamlit with Plotly visualizations
- **Pages**: Batch results, detailed analysis, analyst alignment, bullish convergence
- **Features**: Interactive filtering, watchlist management, real-time API integration

### Data Flow Architecture

```
Stock Lists (CSV) → Batch Analysis → Method Comparison → Convergence Analysis → Dashboard/API
```

## Setup and Installation

### Prerequisites
- Python 3.8+
- Required packages: `pip install -r requirements.txt`
- Dashboard packages: `pip install -r requirements_dashboard.txt`

### API Server
```bash
python run_api.py
```
- Server: http://localhost:8000
- Documentation: http://localhost:8000/docs

### Dashboard
```bash
python run_dashboard.py
```
- Dashboard: http://localhost:8501

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

**API Endpoints:**
- `POST /analyze/{ticker}` - Single stock comprehensive analysis
- `POST /batch/upload` - Batch analysis via CSV upload
- `GET /batch/{job_id}/status` - Monitor batch job progress
- `GET /batch/{job_id}/results` - Retrieve batch results

## Key Features

### Multi-Method Valuation
- **4 Core Methods**: DCF, Technical, Comparable, Startup
- **Consensus Scoring**: Weighted recommendations across methods
- **Quality Adjustment**: Analysis confidence based on data quality

### Analyst Alignment Analysis
- **Alignment Categories**: Investment_Aligned, Precise_Aligned, Moderate_Aligned, Divergent
- **Performance Metrics**: Method-specific alignment rates and deviation scores
- **Bullish Convergence**: Identification of high-conviction opportunities

### Interactive Dashboard
- **Real-time Filtering**: Dynamic analysis based on user criteria
- **Watchlist Management**: Build and analyze custom stock portfolios
- **Batch Processing**: Analyze entire watchlists with progress tracking
- **Visual Analytics**: Charts and metrics for quick decision making

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
│   ├── analyzers/          # Individual analysis methods
│   └── batch/              # Batch processing services
├── dashboard/              # Streamlit dashboard components
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

This framework provides end-to-end stock analysis capabilities from bulk processing to detailed individual analysis, with professional-grade alignment validation and interactive exploration tools.