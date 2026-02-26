# User Guide - Stock Analysis Dashboard

## - DISCLAIMER

This is a personal project to analyse stocks for investment. The outputs of this project are not intended as investment advice. Carry out your own research for stock investments.

## - What does this project do

The idea is to run basic quant analysis such as DCF, Technical against one or multiple stocks to derive a share price value. Compare the derived share value with value predicted by analysts on Yahoo Finance (available from yahoo finance api)

Where 1 or more of the quant analysis matches, the stock may be considered for further analysis.

*** NOT intended as investment advice ***

## Table of Contents
1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Thesis Generation](#thesis-generation)
4. [Historical Analysis](#historical-analysis)
5. [Batch Analysis](#batch-analysis)
6. [Watchlist Management](#watchlist-management)
7. [Tips & Best Practices](#tips--best-practices)

---

## Getting Started

### Accessing the Dashboard

1. **Start the dashboard**:
   ```bash
   python run_dashboard.py
   ```

2. **Open in browser**:
   ```
   http://localhost:8501
   ```

3. **First-time setup**:
   - Ensure API is running (`python run_api.py`)
   - Verify database connection in `.env`
   - Check LLM API keys are configured

---

## Dashboard Overview

### Main Navigation

The dashboard has several pages accessible from the sidebar:

Main functionality:-
- **🏠 Home** - Quick analysis and overview
- **📈 Thesis Generation** - Generate professional investment theses
- **📜 Historical Analysis** - View past analyses from database

Under Build / Older deprecated: -
- **📊 Batch Results** - View batch analysis results
- **🔍 Detailed Analysis** - Deep-dive into individual stocks
- **👥 Analyst Alignment** - Compare methods vs analyst consensus
- **🎯 Bullish Convergence** - Multi-method agreement analysis
- **⭐ Watchlist** - Manage custom stock lists

---

## Thesis Generation

**Location**: Thesis Generation page in sidebar

### What It Does

Generates professional-grade investment theses using LLM analysis, similar to Seeking Alpha quality reports.

### Step-by-Step Guide

#### 1. Enter Stock Ticker

```
┌─────────────────────────────────┐
│ Enter Stock Ticker: [AAPL    ] │
│                     [Analyze]   │
└─────────────────────────────────┘
```

- Type ticker symbol (e.g., AAPL, MSFT, TSLA)
- Click "Analyze" button
- Wait 10-30 seconds for analysis to complete

#### 2. View Analysis Overview

After analysis completes, you'll see:

**Summary Cards** (Top of page):
```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Current Price│ Target Price │ Upside       │ Recommendation│
│ $175.50      │ $195.25      │ +11.2%       │ Buy          │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

**Company Information**:
- Business summary
- Industry and sector
- Company type classification
- Key financial metrics

#### 3. Explore Analysis Tabs

The page has 13 tabs with detailed analysis:

**Overview Tab**:
- Business summary
- Company information
- Key metrics (Market Cap, P/E, ROE, etc.)
- Dividend information
- Forward-looking metrics

**DCF Tab**:
- Discounted cash flow valuation
- Fair value calculation
- Free cash flow projections
- WACC breakdown
- Terminal value

**Technical Tab**:
- Price patterns and trends
- Technical indicators (RSI, MACD, Bollinger Bands)
- Support/resistance levels
- Fibonacci retracements
- Pivot points
- Trading signals

**Comparable Tab**:
- Peer company valuation
- Valuation multiples (P/E, P/B, P/S)
- Sector comparison
- Relative valuation

**AI Insights Tab**:
- LLM-powered business analysis
- Growth prospects
- Competitive advantages
- Risk assessment

**Analyst Consensus Tab**:
- Professional analyst targets
- Consensus recommendation
- Price target range
- Analyst count

**News Tab**:
- Recent news articles
- Sentiment analysis
- Key events
- Market impact

**Other Tabs**:
- Business Model
- Financial Health
- Industry Analysis
- Competitive Position
- Management Quality

#### 4. Generate Investment Thesis

**Scroll down to "Generate Investment Thesis" section**:

```
┌─────────────────────────────────────────────────┐
│ Generate Investment Thesis                      │
│                                                 │
│ Select LLM Provider: [Groq Llama-3.3 🚀    ▼] │
│                                                 │
│ Select Thesis Type:                            │
│ ○ Bull Case - Optimistic investment thesis     │
│ ● Balanced - Objective analysis (recommended)  │
│ ○ Bear Case - Conservative/skeptical view      │
│                                                 │
│ [Generate Thesis]                              │
└─────────────────────────────────────────────────┘
```

**Steps**:

1. **Choose LLM Provider**:
   - Groq Llama-3.3 (Recommended - Fast & Free)
   - OpenAI GPT-4o-mini (High quality)
   - xAI Grok (Alternative)

2. **Select Thesis Type**:
   - **Bull Case**: Optimistic view, focuses on opportunities
   - **Balanced**: Objective analysis (recommended for most cases)
   - **Bear Case**: Conservative view, focuses on risks

3. **Click "Generate Thesis"**:
   - Takes 10-20 seconds
   - Uses all analysis data
   - Generates professional-quality report

#### 5. Review Generated Thesis

The thesis includes:

**Investment Thesis Summary**:
- Executive summary
- Key investment highlights
- Risk factors

**Business Overview**:
- Company description
- Business model
- Competitive position

**Financial Analysis**:
- Revenue trends
- Profitability metrics
- Cash flow analysis
- Balance sheet strength

**Valuation Assessment**:
- Current valuation
- Fair value estimate
- Valuation methodology
- Price target justification

**Risk Analysis**:
- Key risks
- Mitigating factors
- Risk rating

**Investment Recommendation**:
- Final recommendation
- Time horizon
- Entry/exit points

#### 6. View Financial Charts

**Click "View Financial Charts" button**:

```
┌─────────────────────────────────────────┐
│ [View Financial Charts]                 │
└─────────────────────────────────────────┘
```

**Charts Available**:
- **Revenue Trend**: Quarterly/Annual revenue (blue bars)
- **Income Trend**: Net income over time (green/red bars)
- **Cash Flow Trend**: Operating/Free cash flow (multi-color bars)

**Chart Features**:
- Chronological ordering (oldest to newest)
- Hover for exact values
- Maximize/restore modal
- Color-coded legends

#### 7. Export or Save

**Options**:
- Copy thesis text for reports
- Take screenshots of charts
- Save analysis to database (automatic)
- Export to PDF (browser print function)

---

## Historical Analysis

**Location**: Historical Analysis page in sidebar

### Pre-requisite

Run python -m src.share_insights_v1.tests.test_batch_analysis [nasdaq / nyse / asx / nzx]
Directory src/share_insights_v1/resources/stock_dump includes stock dumps in files - nasdaq.csv, nyse.csv, so on. 

Running the test file will run a basic quant analysis deriving - DCF / Startup, technical, Comparable, Yahoo Finance Analsyst Data and storing it in the DB. 

Each run creates a batch job and analysis for each ticker is stored in the DB against a batch job id. So multiple runs on the same stock list like nasdaq.csv can be differentiated by the run time available on the UI in historical analysis - 'Bulk Analysis'

### What It Does

View and search past analyses stored in the PostgreSQL database.

### Step-by-Step Guide

#### 1. Access Historical Analysis Page

Click "📜 Historical Analysis" in sidebar

#### 2. Search and Filter

**Search Options**:

```
┌─────────────────────────────────────────────────┐
│ Search by Ticker: [AAPL                      ] │
│                                                 │
│ Filter by Date Range:                          │
│ From: [2024-01-01] To: [2024-12-31]           │
│                                                 │
│ Filter by Recommendation:                      │
│ ☑ Strong Buy  ☑ Buy  ☑ Hold  ☑ Sell          │
│                                                 │
│ Filter by Quality Grade:                       │
│ ☑ A  ☑ B  ☑ C  ☐ D  ☐ F                      │
│                                                 │
│ [Apply Filters]  [Clear Filters]              │
└─────────────────────────────────────────────────┘
```

**Filter Options**:
- **Ticker**: Search specific stock
- **Date Range**: Filter by analysis date
- **Recommendation**: Filter by buy/sell/hold
- **Quality Grade**: Filter by analysis quality (A-F)
- **Company Type**: Mature/Growth/Startup/Financial
- **Sector/Industry**: Filter by sector

#### 3. View Results Table

**Results Display**:

```
┌──────┬────────┬──────────┬──────────────┬───────────┬──────┐
│Ticker│ Date   │ Current  │ Target Price │ Recommend │Grade │
│      │        │ Price    │              │           │      │
├──────┼────────┼──────────┼──────────────┼───────────┼──────┤
│AAPL  │12/15/24│ $175.50  │ $195.25      │ Buy       │  A   │
│MSFT  │12/14/24│ $380.25  │ $425.00      │ Strong Buy│  A   │
│TSLA  │12/13/24│ $245.80  │ $220.00      │ Sell      │  B   │
└──────┴────────┴──────────┴──────────────┴───────────┴──────┘
```

**Table Features**:
- Sortable columns (click header)
- Pagination (if many results)
- Color-coded recommendations
- Quality grade indicators

#### 4. View Detailed Analysis

**Click on any row** to expand details:

```
┌─────────────────────────────────────────────────┐
│ AAPL - Detailed Analysis (12/15/2024)          │
│                                                 │
│ Final Recommendation: Buy                      │
│ Consensus Score: 1.05                          │
│ Target Price: $195.25                          │
│ Confidence: High                               │
│ Risk Level: Medium                             │
│                                                 │
│ Individual Analyzer Results:                   │
│ ├─ DCF: Buy ($185.00)                         │
│ ├─ Technical: Hold ($175.00)                  │
│ ├─ Comparable: Strong Buy ($195.00)           │
│ ├─ Analyst Consensus: Buy ($190.00)           │
│ └─ AI Insights: Buy ($188.00)                 │
│                                                 │
│ [View Full Analysis] [Compare with Current]    │
└─────────────────────────────────────────────────┘
```

#### 5. Compare Historical vs Current

**Click "Compare with Current"**:
- Runs new analysis for same ticker
- Shows side-by-side comparison
- Highlights changes in recommendation
- Shows price movement since analysis

**Comparison View**:

```
┌─────────────────────────────────────────────────┐
│ Historical (12/15/24)  │  Current (01/05/25)   │
├────────────────────────┼───────────────────────┤
│ Price: $175.50         │  Price: $185.25       │
│ Target: $195.25        │  Target: $200.00      │
│ Recommend: Buy         │  Recommend: Buy       │
│ Confidence: High       │  Confidence: High     │
│                        │                       │
│ Change: +5.6% price increase                  │
│ Status: Still undervalued                     │
└─────────────────────────────────────────────────┘
```

#### 6. Export Historical Data

**Export Options**:

```
┌─────────────────────────────────────────────────┐
│ Export Data                                     │
│                                                 │
│ [Download as CSV]  [Download as Excel]         │
│                                                 │
│ Include:                                        │
│ ☑ Summary data                                 │
│ ☑ Individual analyzer results                  │
│ ☑ Financial metrics                            │
│ ☐ Full analysis JSON                           │
└─────────────────────────────────────────────────┘
```

#### 7. Track Performance

**Performance Tracking**:
- Compare historical target prices vs actual prices
- Calculate recommendation accuracy
- Track portfolio performance
- Identify best-performing analysis methods

**Performance Metrics**:
```
┌─────────────────────────────────────────────────┐
│ Analysis Performance (Last 30 Days)            │
│                                                 │
│ Total Analyses: 150                            │
│ Accurate Recommendations: 68%                  │
│ Average Target Price Accuracy: ±12%            │
│                                                 │
│ Best Performing Analyzer: DCF (75% accuracy)   │
│ Most Reliable: Analyst Consensus (70%)         │
└─────────────────────────────────────────────────┘
```

---

## Batch Analysis

### Quick Batch Analysis

**Location**: Home page or Batch Results page

#### 1. Upload Stock List

```
┌─────────────────────────────────────────────────┐
│ Upload CSV File                                 │
│                                                 │
│ [Choose File] nasdaq.csv                       │
│                                                 │
│ CSV Format:                                     │
│ Symbol,Security Name                           │
│ AAPL,Apple Inc.                                │
│ MSFT,Microsoft Corporation                     │
│                                                 │
│ [Upload and Analyze]                           │
└─────────────────────────────────────────────────┘
```

#### 2. Monitor Progress

```
┌─────────────────────────────────────────────────┐
│ Analysis Progress                               │
│                                                 │
│ ████████████████░░░░░░░░░░░░░░░░ 45%          │
│                                                 │
│ Completed: 45 / 100 stocks                     │
│ Estimated time remaining: 8 minutes            │
│                                                 │
│ Current: Analyzing TSLA...                     │
└─────────────────────────────────────────────────┘
```

#### 3. View Results

Results automatically display when complete:
- Summary statistics
- Top picks (Strong Buy recommendations)
- Filterable results table
- Export options

---

## Watchlist Management

**Location**: Watchlist page in sidebar

### Create Watchlist

```
┌─────────────────────────────────────────────────┐
│ Create New Watchlist                            │
│                                                 │
│ Name: [Tech Growth Stocks              ]       │
│                                                 │
│ Add Tickers (comma-separated):                 │
│ [AAPL, MSFT, GOOGL, AMZN, META        ]       │
│                                                 │
│ [Create Watchlist]                             │
└─────────────────────────────────────────────────┘
```

### Analyze Watchlist

```
┌─────────────────────────────────────────────────┐
│ My Watchlists                                   │
│                                                 │
│ ○ Tech Growth Stocks (5 stocks)                │
│ ○ Dividend Aristocrats (12 stocks)             │
│ ○ Small Cap Value (8 stocks)                   │
│                                                 │
│ [Analyze Selected]  [Edit]  [Delete]           │
└─────────────────────────────────────────────────┘
```

---

## Tips & Best Practices

### For Thesis Generation

1. **Use Balanced Thesis First**:
   - Most objective view
   - Good for initial research
   - Then generate Bull/Bear for different perspectives

2. **Check Multiple Tabs**:
   - Don't rely on just one analyzer
   - Compare DCF vs Comparable vs Technical
   - Look for consensus across methods

3. **Review Financial Charts**:
   - Verify revenue growth trends
   - Check profitability consistency
   - Assess cash flow stability

4. **Consider Quality Grade**:
   - Grade A/B: High confidence
   - Grade C: Moderate confidence
   - Grade D/F: Low confidence, missing data

5. **LLM Provider Selection**:
   - Groq: Fast, free, good quality (recommended)
   - OpenAI: Highest quality, costs money
   - xAI: Alternative if others fail

### For Historical Analysis

1. **Track Your Decisions**:
   - Review past analyses before new investments
   - Learn from accurate/inaccurate predictions
   - Identify which analyzers work best for you

2. **Compare Over Time**:
   - Run same stock monthly
   - Track recommendation changes
   - Identify trend reversals

3. **Performance Analysis**:
   - Calculate actual returns vs predicted
   - Identify best-performing methods
   - Adjust strategy based on results

4. **Use Filters Effectively**:
   - Filter by quality grade for high-confidence analyses
   - Filter by date for recent analyses
   - Filter by recommendation for specific strategies

### General Best Practices

1. **Always Run Fresh Analysis**:
   - Market conditions change
   - Don't rely on old analyses
   - Re-analyze before making decisions

2. **Diversify Analysis Methods**:
   - Don't rely on single method
   - Look for multi-method agreement
   - Higher confidence when methods align

3. **Understand Limitations**:
   - News data may be stale for small-caps
   - DCF not applicable for financials
   - SEC data only for US companies

4. **Save Important Analyses**:
   - Database stores automatically
   - Export to CSV for records
   - Screenshot charts for presentations

5. **Monitor API Costs**:
   - Groq is free (recommended)
   - OpenAI charges per request
   - xAI has usage limits

---

## Keyboard Shortcuts

- **Ctrl+R**: Refresh page
- **Ctrl+F**: Search in page
- **Esc**: Close modals
- **Tab**: Navigate between fields

---

## Troubleshooting

### Thesis Generation Issues

**"Analysis failed"**:
- Check API is running
- Verify ticker symbol is valid
- Check internet connection

**"LLM generation failed"**:
- Try different LLM provider
- Check API keys in .env
- Verify provider has credits

**"No financial data"**:
- Stock may be delisted
- Data provider issue
- Try again later

### Historical Analysis Issues

**"No results found"**:
- Check date range
- Verify ticker spelling
- Clear filters and try again

**"Database connection error"**:
- Check DATABASE_URL in .env
- Verify PostgreSQL is running
- Check database exists

---

## Support

- **Documentation**: See ARCHITECTURE.md for technical details
- **Issues**: Report bugs via GitHub Issues
- **Security**: See SECURITY.md for vulnerability reporting

---

**Last Updated**: 2025-01-XX
**Version**: 1.0
