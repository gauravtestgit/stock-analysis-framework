import yfinance as yf
import pandas as pd

def get_revenue_trend(ticker):
    """Get revenue trend from yfinance"""
    
    stock = yf.Ticker(ticker)
    
    # Method 1: From income statement (quarterly and annual)
    quarterly_income = stock.quarterly_income_stmt
    annual_income = stock.income_stmt
    
    # Method 2: From financials (same as income_stmt)
    quarterly_financials = stock.quarterly_financials
    annual_financials = stock.financials
    
    # Extract revenue data
    revenue_data = {}
    
    # Annual revenue
    if not annual_income.empty and 'Total Revenue' in annual_income.index:
        annual_revenue = annual_income.loc['Total Revenue'].dropna()
        revenue_data['annual_revenue'] = annual_revenue.to_dict()
        
        # Calculate growth rates
        revenue_values = annual_revenue.values
        if len(revenue_values) >= 2:
            recent_growth = (revenue_values[0] - revenue_values[1]) / revenue_values[1] * 100
            revenue_data['recent_annual_growth'] = recent_growth
    
    # Quarterly revenue
    if not quarterly_income.empty and 'Total Revenue' in quarterly_income.index:
        quarterly_revenue = quarterly_income.loc['Total Revenue'].dropna()
        revenue_data['quarterly_revenue'] = quarterly_revenue.to_dict()
        
        # Calculate QoQ growth
        revenue_values = quarterly_revenue.values
        if len(revenue_values) >= 2:
            qoq_growth = (revenue_values[0] - revenue_values[1]) / revenue_values[1] * 100
            revenue_data['recent_quarterly_growth'] = qoq_growth
    
    # Method 3: From info (current metrics)
    info = stock.info
    revenue_data['current_revenue'] = info.get('totalRevenue', 0)
    revenue_data['revenue_growth'] = info.get('revenueGrowth', 0)
    revenue_data['quarterly_revenue_growth'] = info.get('quarterlyRevenueGrowth', 0)
    
    return revenue_data

# Example usage
if __name__ == "__main__":
    ticker = "AAPL"
    revenue_trend = get_revenue_trend(ticker)
    
    print(f"Revenue trend for {ticker}:")
    print(f"Current revenue: ${revenue_trend.get('current_revenue', 0):,.0f}")
    print(f"Revenue growth: {revenue_trend.get('revenue_growth', 0):.2%}")
    print(f"Recent annual growth: {revenue_trend.get('recent_annual_growth', 0):.2f}%")
    print(f"Recent quarterly growth: {revenue_trend.get('recent_quarterly_growth', 0):.2f}%")
    
    # Show historical annual revenue
    if 'annual_revenue' in revenue_trend:
        print("\nHistorical Annual Revenue:")
        for date, revenue in revenue_trend['annual_revenue'].items():
            print(f"{date.strftime('%Y')}: ${revenue:,.0f}")