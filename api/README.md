# Stock Analysis API

FastAPI wrapper for the stock_analyzer.py functionality.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the API:
```bash
python main.py
```

3. Test the API:
```bash
python test_api.py
```

## Endpoints

### GET /health
Health check endpoint

### POST /analyze/{ticker}
Analyze a single stock
- Path parameter: `ticker` (string)
- Optional query parameter: `config` (dict)

### POST /analyze
Analyze a single stock with request body
```json
{
    "ticker": "AAPL",
    "config": {
        "default_cagr": 0.05,
        "max_cagr_threshold": 0.15
    }
}
```

### POST /analyze/batch
Analyze multiple stocks
```json
{
    "tickers": ["AAPL", "MSFT", "GOOGL"],
    "config": {
        "default_cagr": 0.05,
        "max_cagr_threshold": 0.15
    }
}
```

## API Documentation

Once running, visit:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)