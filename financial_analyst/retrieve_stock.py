import yfinance as yf
import pandas as pd
import dcf_yf
import os
import traceback
import cagr_calculations

def read_stock_data(file_path) -> pd.DataFrame:
    # Read NASDAQ data from CSV file
    df = pd.read_csv(file_path)
    return df

def save_analysis(stock_data, write_header=False):
    row_df = pd.DataFrame([stock_data], columns=['Symbol', 'DCF Price', 'Last Close'])
    row_df.to_csv('C:/Users/x_gau/source/repos/agentic/langchain/tutorials/finance-app/financial_analyst/resources/stock_analysis.csv', 
                  index=False, mode='a', header=write_header)
    return

def read_stock_from_file():
    df = read_stock_data('C:/Users/x_gau/source/repos/agentic/langchain/tutorials/finance-app/financial_analyst/resources/nasdaq2.csv')
    print(len(df['Symbol']))
    count = 0
    stock_data = []
    #stock_analysis_df = pd.DataFrame(stock_data, columns=['Symbol', 'DCF Price', 'Last Close'])
    for symbol in df['Symbol']:
        try:
            count += 1
            print(f'Processing stock {count}...', end='\r', flush=True)
            
            ticker = dcf_yf.get_stock_ticker_object(symbol)
            dcf_share_price = dcf_yf.get_share_price(symbol, 0.1, 0.05, 0.2, 0.05, 10)
            # print(f'Ticker: {symbol}, DCF Price: ${dcf_share_price:,.2f}, Last Close: ${ticker.info["regularMarketPrice"]:,.2f}')
            stock_data = [symbol, f'{dcf_share_price:,.2f}', ticker.info.get("previousClose", 0)]
            save_analysis(stock_data, write_header=(count==1))
            
        except Exception as e:
            #print(f'Symbol: {symbol}, Error: {str(e)}')
            stock_data = [symbol, f'error: {str(e)}', ticker.info.get("previousClose", 0)]
            save_analysis(stock_data, write_header=(count==1))
            continue
    return

def debug_call(symbol):
    os.environ['DEBUG'] = 'true'
    #ticker = dcf_yf.get_stock_ticker_object(symbol)
    market_return = 0.08
    cost_of_debt = 0.04
    tax_rate = .21
    terminal_growth_rate = 0.025
    years = 5
    dcf_yf.get_share_price(symbol, market_return=0.08,
                            cost_of_debt=0.04, tax_rate=0.21,
                            terminal_growth_rate=0.025, years=5)
    return

if __name__ == "__main__":
    
    os.environ['DEBUG'] = 'true'
    

    #read_stock_from_file()
    debug_call('aal')
    # ticker = dcf_yf.get_stock_ticker_object('aal')
    # fcf_data = ticker.cashflow.loc['Free Cash Flow'].dropna()
    # fcf_values = fcf_data.values
    # print(fcf_values)
    # print(cagr_calculations.get_cagr(fcf_values, simple_cagr=True))
    # ebitda_data = ticker.income_stmt.loc['EBITDA'].dropna()
    # ebitda_values = ebitda_data.values
    # print(ebitda_values)
    # print(cagr_calculations.get_cagr(ebitda_values, simple_cagr=True))
    # #cagr = cagr_calculations.calculate_traditional_cagr_with_outliers(fcf_values,0.15)
    # print(f'traditional cagr: {cagr}')
    # cagr = cagr_calculations.calculate_median_growth_rate(fcf_values)
    # print(f'median growth rate cagr: {cagr}')
    # cagr = cagr_calculations.calculate_average_growth_rate(fcf_values)
    # print(f'average growth rate cagr: {cagr}')