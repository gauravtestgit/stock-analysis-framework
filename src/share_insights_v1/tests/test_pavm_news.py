import yfinance as yf
from datetime import datetime

ticker = "PAVM"
stock = yf.Ticker(ticker)
news_data = stock.news

print(f"\n{'='*80}")
print(f"Total news articles returned by yfinance for {ticker}: {len(news_data)}")
print(f"{'='*80}\n")

for i, news_item in enumerate(news_data[:10], 1):
    content = news_item.get('content', {})
    title = content.get('title', 'No title')
    pub_date = content.get('pubDate', '')
    
    # Parse date
    if pub_date:
        try:
            news_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            formatted_date = news_date.strftime('%Y-%m-%d %H:%M')
        except:
            formatted_date = pub_date
    else:
        formatted_date = 'No date'
    
    print(f"{i}. [{formatted_date}] {title[:80]}")

print(f"\n{'='*80}\n")
