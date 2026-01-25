import yfinance as yf

# Test with DELL
ticker = "DELL"
stock = yf.Ticker(ticker)
info = stock.info

print(f"\n{'='*80}")
print(f"Yahoo Finance Fields for {ticker}")
print(f"{'='*80}\n")

# Check all forward-looking fields
forward_fields = [
    'forwardPE', 'forwardEps', 'targetMeanPrice', 'targetMedianPrice', 
    'targetHighPrice', 'targetLowPrice', 'numberOfAnalystOpinions',
    'epsForward', 'epsCurrentYear', 'epsNextYear', 'epsNextQuarter',
    'epsTrailingTwelveMonths', 'earningsQuarterlyGrowth', 
    'longTermPotentialGrowthRate', 'earningsGrowth', 'revenueGrowth',
    'earningsDate', 'earningsTimestamp', 'epsRevisionsUp', 'epsRevisionsDown',
    'lastEarningsSurprise', 'lastEarningsSurprisePct', 'earningsSurprise',
    'earningsSurprisePct', 'dividendRate', 'dividendYield'
]

print("FORWARD-LOOKING FIELDS:")
print("-" * 80)
for field in forward_fields:
    value = info.get(field, 'NOT FOUND')
    print(f"{field:35} = {value}")

print(f"\n{'='*80}")
print("ALL AVAILABLE FIELDS (first 50):")
print(f"{'='*80}\n")
for i, (key, value) in enumerate(info.items()):
    if i >= 50:
        break
    print(f"{key:35} = {value}")

print(f"\n\nTotal fields available: {len(info)}")
