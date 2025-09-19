import yfinance as yf
import pandas as pd
import dcf_yf
import os
import traceback
import financial_analyst.util.cagr_calculations as cagr_calculations
import financial_analyst.util.cash_flow_data_handler as cfh
from config import FinanceConfig
from util.debug_printer import debug_print

def read_stock_data(file_path) -> pd.DataFrame:
    # Read NASDAQ data from CSV file
    df = pd.read_csv(file_path)
    return df

def save_analysis(stock_data, write_header=False):
    row_df = pd.DataFrame([stock_data], columns=['Symbol', 'DCF Price', 'Equity Value', 'Last Close'])
    row_df.to_csv('C:/Users/x_gau/source/repos/agentic/langchain/tutorials/finance-app/financial_analyst/resources/stock_analysis.csv', 
                  index=False, mode='a', header=write_header)
    return

def read_stock_from_file():
    df = read_stock_data('C:/Users/x_gau/source/repos/agentic/langchain/tutorials/finance-app/financial_analyst/resources/nasdaq.csv')
    print(len(df['Symbol']))
    count = 0
    stock_data = []
    config = FinanceConfig()
    config.default_cagr = 0.05
    config.max_cagr_threshold = 0.15
    config.use_default_ebitda_multiple = False
    debug_print(f'default settings\n{vars(config)}')
    #stock_analysis_df = pd.DataFrame(stock_data, columns=['Symbol', 'DCF Price', 'Equity Value', 'Last Close'])
    for symbol in df['Symbol']:
        try:
            count += 1
            print(f'Processing stock {count}...', end='\r', flush=True)
            
            ticker = dcf_yf.get_stock_ticker_object(symbol)
            dcf_share_price, equity_value = dcf_yf.get_share_price(symbol, config=config)
            # print(f'Ticker: {symbol}, DCF Price: ${dcf_share_price:,.2f}, Last Close: ${ticker.info["regularMarketPrice"]:,.2f}')
            stock_data = [symbol, f'{dcf_share_price:,.2f}',f'${equity_value:,.2f}', ticker.info.get("previousClose", 0)]
            save_analysis(stock_data, write_header=(count==1))
            
        except Exception as e:
            #print(f'Symbol: {symbol}, Error: {str(e)}')
            stock_data = [symbol, f'error: {str(e)}', 'N/A', ticker.info.get("previousClose", 0)]
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
    config = FinanceConfig()
    config.default_cagr = 0.05
    config.max_cagr_threshold = 0.15
    config.use_default_ebitda_multiple = False
    print(f'default settings\n{vars(config)}')
    dcf_yf.get_share_price(symbol, config=config)
    return

if __name__ == "__main__":
    
    #os.environ['DEBUG'] = 'true'
    
    read_stock_from_file()
    #debug_call('ampx')
    
    #dcf_yf.get_share_price('AAPL', config = None)
        
