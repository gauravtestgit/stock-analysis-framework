# Final Recommendation and Predicted Price Logic

## Overview
The final recommendation and predicted price are calculated by the `RecommendationService` which consolidates results from multiple analyzers using a weighted consensus approach.

## Process Flow

### 1. Analysis Orchestration
- **File**: `analysis_orchestrator.py`
- **Process**: Runs applicable analyzers in parallel based on company type
- **Timeout**: 60s overall, 30s per analyzer
- **Output**: Individual analyzer results with recommendations and price targets

### 2. Recommendation Consolidation
- **File**: `recommendation_service.py`
- **Process**: Consolidates individual analyzer results into final recommendation

## Analyzer Weights

The system uses different weights for different analyzers:

```python
recommendation_weights = {
    'dcf': 0.25,           # 25% weight
    'comparable': 0.2,     # 20% weight  
    'technical': 0.15,     # 15% weight
    'startup': 0.4,        # 40% weight (for loss-making companies)
    'analyst_consensus': 0.25,  # 25% weight
    'ai_insights': 0.15    # 15% weight
}
```

**Important**: Weights are automatically normalized based on available analyzers:
- **Mature/Growth**: DCF(0.25) + Comparable(0.2) + Technical(0.15) + Analyst(0.25) + AI(0.15) = 1.0 total
- **Startup**: Startup(0.4) + Technical(0.15) + AI(0.15) + Analyst(0.25) = 0.95 → normalized to 1.0
- **Financial**: Comparable(0.2) + Technical(0.15) + Analyst(0.25) + AI(0.15) = 0.75 → normalized to 1.0

**Note**: `news_sentiment` is NOT included in the weighted scoring - only affects risk factors and signals.

## Final Recommendation Logic

### 1. Consensus Score Calculation
Each recommendation is mapped to a numerical score:
- **Strong Buy**: +2
- **Buy**: +1  
- **Speculative Buy**: +1
- **Hold**: 0
- **Monitor**: 0
- **Sell**: -1
- **Strong Sell**: -2

Weighted consensus score = Σ(analyzer_score × analyzer_weight) / total_weight

### 2. Final Recommendation Mapping
Based on consensus score:
- **≥ 1.5**: Strong Buy
- **≥ 0.5**: Buy  
- **≤ -1.5**: Strong Sell
- **≤ -0.5**: Sell
- **Otherwise**: Hold

### 3. Confidence Level
- **High**: ≥3 analyses AND |consensus_score| ≥ 1.0
- **Medium**: ≥2 analyses AND |consensus_score| ≥ 0.5  
- **Low**: Otherwise

## Predicted Price Logic

### 1. Individual Analyzer Price Targets
Each analyzer provides a `predicted_price`:
- **DCF**: Fair value from discounted cash flow
- **Technical**: Target based on technical indicators
- **Comparable**: Fair value from peer multiples
- **Startup**: Valuation from startup metrics
- **Analyst Consensus**: Professional analyst target price
- **AI Insights**: LLM-generated price target

### 2. Weighted Consensus Target Price
- **Excludes**: Zero, null, or invalid prices
- **Formula**: Σ(target_price × analyzer_weight) / total_valid_weight
- **Auto-Normalization**: Weights automatically normalized based on available valid prices
- **Fallback**: Returns None if no valid prices available

### 3. Price Target Validation
Only prices > 0 are included in consensus calculation to avoid:
- Skewing results with zero values
- Including failed analyzer results
- Distorting average with placeholder values

### 4. Automatic Weight Normalization
The system automatically normalizes weights based on available analyzers:

**Example - Financial Company**:
- Available: Comparable(0.2), Technical(0.15), Analyst(0.25), AI(0.15)
- Raw total: 0.75
- Normalized: Comparable(26.7%), Technical(20%), Analyst(33.3%), AI(20%)
- Formula: normalized_weight = raw_weight / total_available_weight

This ensures weights always sum to 100% regardless of which analyzers are applicable or successful.

## Company Type Specific Logic

### Applicable Analyzers by Company Type

**Startup/Loss-Making**:
- Startup (40% weight)
- Technical (15% weight)  
- AI Insights (15% weight)
- News Sentiment (signals only)
- Business Model, Financial Health, Analyst Consensus

**Mature/Growth/Profitable**:
- DCF (25% weight)
- Comparable (20% weight)
- Technical (15% weight)
- Analyst Consensus (25% weight)
- AI Insights (15% weight)
- All other analyzers

**Financial Companies**:
- Comparable (20% weight) - DCF not applicable
- Technical (15% weight)
- Analyst Consensus (25% weight)
- All other analyzers

## Risk and Signal Analysis

### Risk Level Determination
- **High**: ≥50% of analyses have high risk indicators
- **Medium**: Some analyses have risk indicators
- **Low**: No significant risk indicators

### Bullish/Bearish Signals
- **Bullish**: Analyzers with Strong Buy/Buy recommendations
- **Bearish**: Analyzers with Strong Sell/Sell recommendations
- **Technical Trends**: Uptrend/Downtrend signals

## API Response Format

The final recommendation is converted to API format in `service.py`:

```python
'final_recommendation': {
    'ticker': ticker,
    'recommendation': recommendation_value,  # String value
    'consensus_score': upside_potential,     # Percentage upside
    'target_price': target_price,           # Weighted consensus price
    'confidence': confidence_level,         # High/Medium/Low
    'contributing_analyses': signals,       # Bullish + bearish signals
    'reasoning': summary,                   # Analysis summary
    'risk_level': risk_level,              # High/Medium/Low
    'key_risks': risk_factors              # List of risk factors
}
```

## Key Design Decisions

### 1. News Sentiment Exclusion
- News sentiment does NOT contribute to weighted recommendation
- Only affects risk factors and sentiment signals
- Prevents short-term news from overriding fundamental analysis

### 2. Startup Analyzer Priority
- Startup analyzer gets 40% weight for loss-making companies
- Recognizes that traditional valuation methods (DCF, comparable) may not apply
- Focuses on growth metrics and cash runway

### 3. Price Target Validation
- Zero/null prices excluded from consensus
- Prevents failed analyses from distorting results
- Ensures only meaningful price targets contribute

### 4. Parallel Execution
- All analyzers run in parallel for performance
- Individual timeouts prevent one slow analyzer from blocking others
- Graceful degradation if some analyzers fail

## Example Calculation

**Company**: AAPL (Mature Profitable)
**Analyzers Run**: DCF, Comparable, Technical, Analyst Consensus, AI Insights

**Individual Results**:
- DCF: Buy (+1), $180 target, 25% weight
- Comparable: Strong Buy (+2), $185 target, 20% weight  
- Technical: Hold (0), $175 target, 15% weight
- Analyst Consensus: Buy (+1), $190 target, 25% weight
- AI Insights: Buy (+1), $182 target, 15% weight

**Consensus Score**: (1×0.25 + 2×0.20 + 0×0.15 + 1×0.25 + 1×0.15) = 1.05

**Final Recommendation**: Buy (consensus score 1.05 ≥ 0.5)

**Target Price**: (180×0.25 + 185×0.20 + 175×0.15 + 190×0.25 + 182×0.15) = $183.25

**Confidence**: High (5 analyses, |1.05| ≥ 1.0)

This weighted approach ensures that the final recommendation reflects the collective wisdom of multiple analysis methods while giving appropriate weight to each method's reliability and applicability.