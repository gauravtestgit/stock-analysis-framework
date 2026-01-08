# News Sentiment Analysis - Web Scraping & LLM Features Enabled by Default

## Summary of Changes

Both **Web Scraping** and **LLM Sentiment Analysis** are now enabled by default in the backend services for enhanced news sentiment analysis.

## Changes Made

### 1. API Service (`src/share_insights_v1/api/service.py`)
- ✅ **LLM Manager Initialization**: Added automatic LLM manager setup with plugin system support
- ✅ **Web Scraping Enabled**: Set `enable_web_scraping=True` by default in all analyzer registrations
- ✅ **LLM Integration**: Pass LLM manager to NewsSentimentAnalyzer for enhanced analysis
- ✅ **Selective Orchestrator**: Ensured web scraping is enabled even in selective analyzer mode

### 2. Batch Service (`src/share_insights_v1/services/batch/batch_analysis_service.py`)
- ✅ **LLM Manager Initialization**: Added LLM manager setup with fallback support
- ✅ **Web Scraping Enabled**: Set `enable_web_scraping=True` by default
- ✅ **Enhanced Analysis**: Registered NewsSentimentAnalyzer with full LLM capabilities

### 3. Additional Analyzers Enabled
- ✅ **AI_INSIGHTS**: Now registered by default with LLM support
- ✅ **BUSINESS_MODEL**: Added with LLM integration
- ✅ **COMPETITIVE_POSITION**: Added for comprehensive analysis
- ✅ **MANAGEMENT_QUALITY**: Added for qualitative assessment
- ✅ **FINANCIAL_HEALTH**: Added with SEC data integration
- ✅ **INDUSTRY_ANALYSIS**: Added for market context

## Features Now Available by Default

### Web Scraping Features
- **Full Article Content**: Scrapes complete articles from news URLs
- **Smart Content Extraction**: Uses multiple selectors to find article content
- **Ticker-Specific Extraction**: Focuses on content mentioning the specific ticker
- **Fallback Handling**: Graceful degradation when scraping fails

### LLM Sentiment Analysis Features
- **Enhanced Fact Extraction**: Institutional-grade fact blocks for financial modeling
- **Quantitative Evidence**: Extracts specific numbers, dollar amounts, percentages
- **Business Mechanism Analysis**: Explains how news impacts the business
- **Verbatim Quotes**: Captures direct quotes for attribution
- **Structured Data**: Returns JSON-formatted analysis results
- **Confidence Scoring**: Provides confidence levels for sentiment scores

### Advanced Analysis Capabilities
- **Lead Fact Identification**: Pinpoints the specific event or development
- **Impact Assessment**: Rates impact from -1.0 (very negative) to +1.0 (very positive)
- **Thesis Integration**: Structured facts feed into investment thesis generation
- **Fallback Analysis**: Rule-based sentiment when LLM unavailable

## Configuration Details

### Default Settings
```python
# News Sentiment Analyzer Configuration
enable_web_scraping=True        # Web scraping enabled
max_articles=5                  # Process up to 5 articles
debug_mode=False               # Debug logging disabled
llm_manager=LLMManager()       # LLM integration enabled
```

### LLM Provider Support
- **Primary**: OpenAI GPT-4
- **Fallback**: Anthropic Claude-3
- **Fallback**: Groq Mixtral
- **Local**: Ollama (if available)

## Impact on Analysis Quality

### Before Changes
- Basic rule-based sentiment analysis
- Limited to news headlines and summaries
- No deep content analysis
- Simple positive/negative scoring

### After Changes
- **Institutional-grade analysis** with structured fact extraction
- **Full article content** analysis via web scraping
- **LLM-powered insights** with business impact assessment
- **Enhanced accuracy** through ticker-specific content focus
- **Professional-quality** fact blocks for investment decisions

## Verification

Run the verification script to confirm configuration:
```bash
python verify_news_config.py
```

Expected output: All services show "PASS" status with web scraping and LLM features enabled.

## Usage

Both API and batch services now automatically use these enhanced features:

### API Usage
```python
# Single stock analysis - automatically uses web scraping + LLM
POST /analyze/AAPL

# Batch analysis - enhanced sentiment for all stocks
POST /batch/upload
```

### Batch Service Usage
```python
# Batch processing with enhanced news analysis
batch_service = BatchAnalysisService(save_to_db=True)
batch_service.process_csv("input.csv", "output.csv")
```

## Performance Considerations

- **Web Scraping**: Adds 2-5 seconds per article (limited to 5 articles max)
- **LLM Analysis**: Adds 1-3 seconds per article for enhanced fact extraction
- **Fallback**: Graceful degradation to rule-based analysis if needed
- **Timeout Handling**: 10-second timeout per article scrape

The enhanced analysis provides significantly higher quality insights while maintaining reasonable performance through smart limits and fallback mechanisms.