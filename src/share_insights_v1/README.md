## - DISCLAIMER

This is a personal project to analyse stocks for investment. The outputs of this project are not intended as investment advice. Carry out your own research for stock investments.

## - What does this project do

The idea is to run basic quant analysis such as DCF, Technical against one or multiple stocks to derive a share price value. Compare the derived share value with value predicted by analysts on Yahoo Finance (available from yahoo finance api)

Where 1 or more of the quant analysis matches, the stock may be considered for further analysis.

*** NOT intended as investment advice ***

# Share Insights v1 - SOLID Principles Implementation

## Architecture Overview

This implementation follows SOLID principles and clean architecture patterns for financial analysis.

## Folder Structure

```
share_insights_v1/
├── interfaces/                 # Abstract interfaces (Dependency Inversion)
│   ├── data_provider.py       # IDataProvider interface
│   ├── analyzer.py            # IAnalyzer interface  
│   ├── calculator.py          # ICalculator interface
│   └── recommendation.py      # IRecommendationEngine interface
│
├── models/                    # Domain models and data structures
│   ├── company.py            # Company, CompanyType enums
│   ├── financial_metrics.py  # FinancialMetrics dataclass
│   ├── analysis_result.py    # AnalysisResult dataclass
│   └── recommendation.py     # Recommendation dataclass
│
├── implementations/          # Concrete implementations
│   ├── analyzers/           # Analysis implementations
│   │   ├── dcf_analyzer.py  # DCF analysis
│   │   ├── technical_analyzer.py
│   │   ├── comparable_analyzer.py
│   │   └── startup_analyzer.py
│   ├── data_providers/      # Data source implementations
│   │   ├── yahoo_provider.py
│   │   └── analyst_provider.py
│   └── calculators/         # Calculation implementations
│       ├── dcf_calculator.py
│       └── quality_calculator.py
│
├── services/                # Application services
│   └── orchestration/      # Orchestration layer
│       ├── analysis_orchestrator.py
│       └── recommendation_service.py
│
├── config/                  # Configuration and DI
│   ├── settings.py         # Application settings
│   └── container.py        # Dependency injection container
│
└── utils/                   # Shared utilities
    └── exceptions.py        # Custom exceptions
```

## SOLID Principles Applied

1. **Single Responsibility**: Each class has one reason to change
2. **Open/Closed**: Extensible without modification via interfaces
3. **Liskov Substitution**: Implementations are interchangeable
4. **Interface Segregation**: Small, focused interfaces
5. **Dependency Inversion**: Depend on abstractions, not concretions