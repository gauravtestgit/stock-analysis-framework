import requests
import json

# Test the API locally
BASE_URL = "http://localhost:8000"

def test_health():
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check: {response.status_code} - {response.json()}")
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to API. Make sure the server is running on localhost:8000")

def test_single_stock():
    ticker = "AAPL"
    response = requests.post(f"{BASE_URL}/analyze/{ticker}")
    print(f"Single stock analysis ({ticker}): {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        try:
            print(f"Recommendation: {data['analysis']['summary']['recommendation']}")
            print(f"Confidence: {data['analysis']['summary']['confidence']}")
        except KeyError as e:
            print(f"Response structure issue: {e}")
            print(f"Available keys: {list(data.keys())}")
    else:
        print(f"Error: {response.text}")

def test_batch_stocks():
    payload = {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "config": {
            "default_cagr": 0.05,
            "max_cagr_threshold": 0.15
        }
    }
    response = requests.post(f"{BASE_URL}/analyze/batch", json=payload)
    print(f"Batch analysis: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(data)
        print(f"Total: {data.get('total_requested', 0)}, Success: {data.get('successful', 0)}, Failed: {data.get('failed', 0)}")
        for result in data.get('results', []):
            if result.get('status') == 'success':
                try:
                    rec = result['analysis']['summary']['recommendation']
                    print(f"  {result['ticker']}: {rec}")
                except KeyError:
                    print(f"  {result['ticker']}: Analysis incomplete")
            else:
                print(f"  {result['ticker']}: {result.get('error', 'Unknown error')}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    print("Testing Stock Analysis API...")
    test_health()
    # test_single_stock()
    test_batch_stocks()