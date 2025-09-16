import yfinance as yf
import pandas as pd
import numpy as np
import os
from cagr_calculations import get_cagr
from util.debug_printer import debug_print
import beta_calculator
import cash_flow_data_handler as cf_handler
from config import FinanceConfig

calculation_default_params = FinanceConfig()


def get_stock_ticker_object(ticker):
    stock = yf.Ticker(ticker)
    return stock

def get_risk_free_rate(ticker = '^TNX'):
    stock = get_stock_ticker_object(ticker)
    risk_free_rate = yf.Ticker(ticker).info['previousClose']/100
    return risk_free_rate
    
def cost_of_equity(ticker:yf.ticker.Ticker, market_return, risk_free_ticker = '^TNX'):
    #beta = ticker.info['beta']
    
    beta = beta_calculator.BetaCalculator(ticker_symbol=ticker.info.get('symbol')).get_beta_with_fallbacks()
    cost_of_equity = get_risk_free_rate(risk_free_ticker) + beta * (market_return - get_risk_free_rate(risk_free_ticker))
    return cost_of_equity

def get_wacc(ticker, tax_rate, cost_of_debt, cost_of_equity):
    
    total_debt = ticker.info.get('totalDebt', 0)
    debt_to_equity = ticker.info.get('debtToEquity', 0)/100
    debug_print(f'Debt to Equity: {debt_to_equity:.2f}')
    equity_weight = 0
    if debt_to_equity ==0 or debt_to_equity is None:
        equity_weight = 1.0
        debt_weight = 0.0
    else:
        equity_weight = 1/(1+debt_to_equity)
        debt_weight = debt_to_equity/(1+debt_to_equity)
    
    wacc = equity_weight * cost_of_equity + debt_weight * cost_of_debt * (1-tax_rate)
    #wacc = wacc = (equity/(equity+total_debt))*cost_of_equity + (total_debt / (equity+total_debt)) * cost_of_debt * (1-tax_rate)
    return wacc

def get_free_cash_flow_cagr(ticker : yf.ticker.Ticker, simple_cagr:bool = False):
    cashflow = ticker.cashflow
    if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
        fcf_data = cashflow.loc['Free Cash Flow'].dropna()
    else:
        estimated_fcf = cf_handler.CashFlowDataHandler(ticker.info.get('symbol')).estimate_fcf_from_net_income()
        fcf_data = estimated_fcf.dropna() if estimated_fcf is not None else pd.Series()
    if fcf_data is None or fcf_data is None or fcf_data.empty or len(fcf_data) < 2:
        debug_print('No free cash flow data available')
        raise Exception("No Cash Flow Data Available")
    fcf_data = ticker.cashflow.loc['Free Cash Flow'].dropna()
    fcf_values = fcf_data.values
    debug_print(f'FCF Beginning: ${fcf_values[-1]:,.2f}, FCF Ending: ${fcf_values[0]:,.2f}, Period: {len(fcf_values)}')
    cagr = get_cagr(fcf_values, simple_cagr=simple_cagr, 
                    max_threshold=calculation_default_params.max_cagr_threshold,
                    default=calculation_default_params.default_cagr)
    return cagr


def get_simple_cagr(ticker : yf.ticker.Ticker):
    # Remove post validation of the cagr_calculations.get_cagr() function
    # default free cash flow cagr of 5% in case yfinance data is incorrect, includes nan, etc

    fcf_cagr = calculation_default_params.default_cagr
    cashflow = ticker.cashflow
    fcf_ending = cashflow.loc['Free Cash Flow'].iloc[0]
    fcf_beginning = cashflow.loc['Free Cash Flow'].iloc[-1]
    period = len(cashflow.columns)
    i = -1
    # while pd.isna(fcf_beginning) or fcf_beginning < 0:
    #     fcf_beginning = cashflow.loc['Free Cash Flow'].iloc[i]
    #     i = i-1
    # period = period + i

    for i in range(-1, -len(cashflow.columns), -1):
        fcf_beginning = cashflow.loc['Free Cash Flow'].iloc[i]
        if pd.isna(fcf_beginning) or fcf_beginning < 0:
            period = period - 1
        else:
            break

    if period < calculation_default_params.min_data_points:
        debug_print('Insufficient historical fcf data. Returning default .05 fcf cagr')
        return fcf_cagr
    debug_print(f"FCF Ending: ${fcf_ending:,.2f}, FCF Beginning: ${fcf_beginning:,.2f}, Period: {period}")

    if fcf_ending < fcf_beginning:
        debug_print(f'Free cash flow is declining. Returning default cagr: {fcf_cagr}')
        return fcf_cagr
    try:
        fcf_cagr = (fcf_ending/fcf_beginning)**(1/period) - 1
        
    except ZeroDivisionError:
        debug_print("Error: Period is zero")
    except ValueError:
        debug_print("Error: Unable to calculate CAGR - check for negative values")
    except Exception as e:
        debug_print(f"Error calculating FCF CAGR: {str(e)}")
    finally:
        return fcf_cagr

def get_future_cash_flow(ticker : yf.ticker.Ticker, fcf_cagr, years):
    cashflow = ticker.cashflow
    fcf_ending = cashflow.loc['Free Cash Flow'].iloc[0]
    fcf_future = 0
    try:
        fcf_future = fcf_ending * (1 + fcf_cagr)**years
    except Exception as e:
        debug_print(f'Error: {str(e)}')
    finally:
        return fcf_future

def get_ebitda_cagr(ticker : yf.ticker.Ticker, simple_cagr:bool = False):
    ebitda_data = ticker.income_stmt.loc['EBITDA'].dropna()
    ebitda_values = ebitda_data.values
    debug_print(f'Ebitda Beginning: ${ebitda_values[-1]:,.2f}, Ebitda Ending: ${ebitda_values[0]:,.2f}, Period: {len(ebitda_values)}')
    ebitda_cagr = get_cagr(ebitda_values,
                           max_threshold=calculation_default_params.max_cagr_threshold,
                           default=calculation_default_params.default_cagr,
                           simple_cagr=simple_cagr)
    return ebitda_cagr

def get_ebitda_cagr_old(ticker : yf.ticker.Ticker):
    #return post testing the cagr_calculations.get_cagr() function

    ebitda_cagr = 0.05
    income_statement = ticker.income_stmt
    ebitda_ending = income_statement.loc['EBITDA'].iloc[0]
    ebitda_beginning = income_statement.loc['EBITDA'].iloc[-1]
    period = len(income_statement.columns) - 1
    
    try:

        while pd.isna(ebitda_beginning) or ebitda_beginning < 0:
            ebitda_beginning = income_statement.loc['EBITDA'].iloc[period]
            period -= 1
    except Exception as e:        
        debug_print(f'Error: {str(e)}')
        debug_print(f'returning default ebitda cagr')
        return ebitda_cagr
    
        

    if period < 2:
        debug_print('Insufficient historical ebitda data. Returning default .05 ebitda cagr')
        return ebitda_cagr
    debug_print(f'Ebitda Beginning: ${ebitda_beginning:,.2f}, Ebitda Ending: ${ebitda_ending:,.2f}, Period: {period}')

    if ebitda_ending < ebitda_beginning:
        debug_print(f'Ebitda is declining. Returning default cagr: {ebitda_cagr}')
        return ebitda_cagr
    try:
        ebitda_cagr = (ebitda_ending/ebitda_beginning)**(1/period) - 1
    except Exception as e:
        debug_print(f'Error: {str(e)}')
    finally : 
        return ebitda_cagr
    
def get_future_ebitda(ticker : yf.ticker.Ticker, ebitda_cagr, years):
    income_statement = ticker.income_stmt
    ebitda_ending = income_statement.loc['EBITDA'].iloc[0]
    ebitda_future = 0
    try:
        ebitda_future = ebitda_ending * (1 + ebitda_cagr)**years
    except Exception as e:
        debug_print(f'Error: {str(e)}')
    finally:
        return ebitda_future
    
def get_terminal_value_perpetuity_growth(fcf_future, wacc, growth_rate):
    
    if growth_rate > wacc:
        debug_print(f'Error. Growth rate: {growth_rate} must be less than WACC: {wacc}. Using defaults')
        growth_rate = min(calculation_default_params.default_terminal_growth, wacc - 0.005)  # Cap at 2.5% or WACC-0.5%
        debug_print(f"Using adjusted growth rate: {growth_rate:.2%}")

    terminal_value_pg = fcf_future * (1 + growth_rate) / (wacc - growth_rate)
    return terminal_value_pg

def get_terminal_value_ebitda_multiple(ticker: yf.ticker.Ticker, ebitda_future, useDefault:bool = True):
    ev_ebitda_multiple = ticker.info.get('enterpriseToEbitda', calculation_default_params.default_ev_ebitda_multiple)  # default multiple
    if ev_ebitda_multiple is None or ev_ebitda_multiple <= 0 or ev_ebitda_multiple > 20:
        if useDefault:
            debug_print(f"Warning: Invalid EV/EBITDA multiple, using default of {calculation_default_params.default_ev_ebitda_multiple}x")
            ev_ebitda_multiple = calculation_default_params.default_ev_ebitda_multiple
        else:
            debug_print(f'using retrieved EV/EBITDA multiple: {ev_ebitda_multiple}x')
        
    terminal_enterprise_value = ebitda_future * ev_ebitda_multiple
    total_debt = ticker.info.get('totalDebt', 0) or 0
    terminal_equity_value = terminal_enterprise_value - total_debt
    debug_print(f"EV/EBITDA Multiple: {ev_ebitda_multiple:.1f}x")
    debug_print(f"Terminal Enterprise Value: ${terminal_enterprise_value:,.0f}")
    debug_print(f"Less Total Debt: ${total_debt:,.0f}")
    debug_print(f"Terminal Equity Value: ${terminal_equity_value:,.0f}")
    
    return terminal_equity_value

def get_projected_free_cash_flows(ticker: yf.ticker.Ticker, fcf_cagr, years):
    cashflow = ticker.cashflow
    fcf_ending = cashflow.loc['Free Cash Flow'].iloc[0]
    projected_free_cash_flows = []
    for i in range(1, years + 1):
        projected_free_cash_flows.append(fcf_ending * (1 + fcf_cagr)**i)
    return projected_free_cash_flows

def get_present_value_free_cash_flows(projected_free_cash_flows, wacc):
    
    present_value_free_cash_flows = []
    
    for i in range(0, len(projected_free_cash_flows)):
        discount_factor = 1/((1 + wacc)**(i+1))
        present_value_free_cash_flows.append(projected_free_cash_flows[i] * discount_factor)

    return present_value_free_cash_flows

def get_present_value_terminal_value(terminal_value, wacc, years):
    discount_factor = 1/((1 + wacc)**(years))
    return terminal_value * discount_factor

def get_average_terminal_value(terminal_value_pg, terminal_value_ebitda_multiple, simple_avg:bool = True):
    # Handle None values
    if terminal_value_pg is None:
        debug_print("Warning: Using only EBITDA multiple method (perpetuity growth unavailable)")
        return terminal_value_ebitda_multiple
    if terminal_value_ebitda_multiple is None:
        debug_print("Warning: Using only perpetuity growth method (EBITDA multiple unavailable)")
        return terminal_value_pg
    
    if simple_avg:
        return (terminal_value_pg + terminal_value_ebitda_multiple)/2
    
    if terminal_value_pg / terminal_value_ebitda_multiple > 1.5:
        debug_print("Warning: Terminal value perpetuity growth is more than 50% higher than terminal value EBITDA multiple. Adjusting weights")
        return (0.4*terminal_value_pg + 0.6*terminal_value_ebitda_multiple)/2
    elif terminal_value_ebitda_multiple / terminal_value_pg > 1.5:
        debug_print("Warning: Terminal value EBITDA multiple is more than 50% higher than terminal value perpetuity growth. Adjusting weights")
        return (0.6*terminal_value_pg + 0.4*terminal_value_ebitda_multiple)/2
    
    return (terminal_value_pg + terminal_value_ebitda_multiple)/2

def get_adjusted_debt(ticker : yf.ticker.Ticker, enterprise_value):
    total_debt = ticker.info.get('totalDebt', 0) or 0
    total_cash = ticker.info.get('totalCash', 0) or 0

def get_share_price(ticker_symbol, config : FinanceConfig=None):
    global calculation_default_params
    if config is not None:
        calculation_default_params = config
    debug_print(calculation_default_params.max_cagr_threshold)
    market_return = calculation_default_params.market_return
    cost_of_debt = calculation_default_params.cost_of_debt
    tax_rate = calculation_default_params.tax_rate
    terminal_growth_rate = calculation_default_params.default_terminal_growth
    years = calculation_default_params.years
    ticker = get_stock_ticker_object(ticker_symbol)
    cost_equity = cost_of_equity(ticker, market_return)
    debug_print(f'Cost of Equity: {cost_equity}')
    wacc = get_wacc(ticker, tax_rate, cost_of_debt, cost_equity)
    debug_print(f'WACC: {wacc}')
    fcf_future = 0
    ebitda_future = 0
    terminal_value_pg = 0
    terminal_value_ebitda_multiple = 0
    fcf_calculation_error = False
    ebitda_calculation_error = False
    try:
        fcf_cagr = get_free_cash_flow_cagr(ticker, simple_cagr=False)
        debug_print(f'FCF CAGR: {fcf_cagr}')
        fcf_future = get_future_cash_flow(ticker, fcf_cagr, years)
        debug_print(f'FCF Future: {fcf_future:,.2f}')
    except Exception as e:
        debug_print(f'Error: {str(e)}')
        fcf_calculation_error = True
        
    try:
        ebitda_cagr = get_ebitda_cagr(ticker, simple_cagr=False)
        debug_print(f'EBITDA CAGR: {ebitda_cagr}')
        ebitda_future = get_future_ebitda(ticker, ebitda_cagr, years)
        debug_print(f'EBITDA Future: {ebitda_future:,.2f}')    
        
    except Exception as e:
        debug_print(f'Error: {str(e)}')
        ebitda_calculation_error = True
    
    if fcf_calculation_error and ebitda_calculation_error:
        debug_print('Error: Unable to calculate both FCF and EBITDA future values. Using default terminal growth rate')
        raise Exception("FCF and EBITDA Data Unavailable")
    
    terminal_value_pg = get_terminal_value_perpetuity_growth(fcf_future, wacc, terminal_growth_rate)
    debug_print(f"Terminal Value Perpetuity Growth: ${terminal_value_pg:,.0f}")
    terminal_value_ebitda_multiple = get_terminal_value_ebitda_multiple(ticker, ebitda_future, True)
    debug_print(f"Terminal Value EBITDA Multiple: ${terminal_value_ebitda_multiple:,.0f}")
    average_terminal_value = get_average_terminal_value(terminal_value_pg, terminal_value_ebitda_multiple)
    debug_print(f'Average Terminal Value: ${average_terminal_value:,.0f}')
    
    projected_free_cash_flows = get_projected_free_cash_flows(ticker, fcf_cagr, years)
    for i in range(0, len(projected_free_cash_flows)):
        debug_print(f'Year :{i+1}, projected FCF: ${projected_free_cash_flows[i]:,.0f}')

    present_value_free_cash_flows = get_present_value_free_cash_flows(projected_free_cash_flows,wacc)
    for i in range(0, len(present_value_free_cash_flows)):
        debug_print(f"Year {i + 1}: PV FCF: ${present_value_free_cash_flows[i]:,.0f}")
    pv_fcf = sum(present_value_free_cash_flows)
    debug_print(f'PV FCF: ${pv_fcf:,.0f}')
    pv_terminal_value = get_present_value_terminal_value(average_terminal_value, wacc, years)
    debug_print(f'PV Terminal Value: ${pv_terminal_value:,.0f}')

    enterprise_value = pv_fcf + pv_terminal_value
    debug_print(f'Enterprise Value: ${enterprise_value:,.0f}')

    total_debt = ticker.info.get('totalDebt', 0) or 0
    total_cash = ticker.info.get('totalCash', 0) or 0
    adjusted_debt = (total_debt - total_cash,0)
    equity_value = enterprise_value - total_debt #+ ticker.info.get('totalCash',0)
    if equity_value < enterprise_value *0.8:
        debug_print('High leverage detected. Adjusting equity')

    debug_print(f'Equity Value: ${equity_value:,.0f}')

    share_price = equity_value / ticker.info.get('sharesOutstanding', 0)
    debug_print(f'Share Price: ${share_price:.2f}')
    debug_print(f'Ticker, DCF Share Price, Last Close Price\n{ticker_symbol}, ${share_price:.2f}, ${ticker.info["previousClose"]:.2f}')
    return share_price, equity_value

# def debug_print(*args, **kwargs):
#     DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

#     if DEBUG:
#         print(*args, **kwargs)

if __name__ == "__main__":
    ticker_symbol = "bot.ax"
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    ticker = get_stock_ticker_object(ticker_symbol)
    #debug_print(ticker.info)
    market_return = 0.08
    cost_of_debt = 0.04
    tax_rate = .21
    terminal_growth_rate = 0.025
    years = 5

    share_price = get_share_price(ticker_symbol, calculation_default_params)
    debug_print(f'Share Price: ${share_price:.2f}')
    
    
    