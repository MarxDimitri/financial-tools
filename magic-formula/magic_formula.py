# Dot not forget to install dependencies
# !pip install financetoolkit financedatabase -U
# pip install openpyxl
# The lib for equity selection - https://github.com/JerBouma/FinanceToolkit/tree/main/financetoolkit/base

import argparse
import financedatabase as fd
from financetoolkit import Toolkit
import pandas as pd
from config import API_KEY, HEAD, COUNTRY, MARKET_CAP, OUTPUTFILE, INDUSTRY
from datetime import datetime

#https://www.jeroenbouma.com/projects/financedatabase/dupont-analysis
def get_tickers(head, country, market_cap):
    equities = fd.Equities()
    return equities.search(country=country, market_cap=market_cap).head(head).index.values.tolist()

def get_beginning_of_year(year):
    return datetime(year, 1, 1).strftime("%Y-%m-%d")

def get_current_year_beginning():
    return get_beginning_of_year(datetime.now().year)

def get_previous_year_beginning():
    return get_beginning_of_year(datetime.now().year - 1)

def get_ratios_and_price(api_key, ticker, start_date):
    companies = Toolkit(
        ticker,
        api_key,
        start_date=start_date,
        sleep_timer=True,
        remove_invalid_tickers=True,
        custom_ratios=custom_ratios,
        progress_bar=False,
        
    )
    try:
        ratios = companies.ratios.collect_custom_ratios()
        quote = companies.get_quote()
        price = quote.loc['Price', ticker]
        return ratios, price
    except Exception as e:
        print(f"Error fetching ratios for {ticker}: {e}")
        return None

custom_ratios = {
    "Net Income": "Net Income",
    "Income Tax Expense": "Income Tax Expense",
    "Interest Expense": "Interest Expense",
    "Weighted Average Shares": "Weighted Average Shares",
    "Fixed Assets": "Fixed Assets",
    "Total Current Assets": "Total Current Assets", 
    "Total Current Liabilities": "Total Current Liabilities",
    "Working Capital": "Working Capital",
    "Total Debt": "Total Dept",
}

def filter_valid_tickers(tickers):
    valid_tickers = [ticker for ticker in tickers if '.' not in ticker or ('.' in ticker and len(ticker.split('.')[-1]) > 2)]
    return valid_tickers

def calc_magic_formula(api_key, head, country, market_cap, outputfile):
    combined_ratios = []
    tickers_with_data = []

    tickers = get_tickers(head, country, market_cap)
    tickers = filter_valid_tickers(tickers)
    print(tickers)

    for ticker in tickers:
            result = get_ratios_and_price(api_key, ticker, get_current_year_beginning())
            if result is None:
                # Retry with the previous year if failed
                result = get_ratios_and_price(api_key, ticker, get_previous_year_beginning())
                if result is None:
                    continue

            ratios_df, price = result

            net_income = ratios_df.iloc[0][0] 
            income_tax_expense= ratios_df.iloc[1][0]
            interest_expense = ratios_df.iloc[2][0]
            weighted_average_shares = ratios_df.iloc[3][0]
            fixed_assets = ratios_df.iloc[4][0]
            total_current_assets = income_tax_expense= ratios_df.iloc[5][0]
            total_current_liabilities = income_tax_expense= ratios_df.iloc[6][0]
            working_capital = income_tax_expense= ratios_df.iloc[7][0]
            total_dept = income_tax_expense= ratios_df.iloc[8][0]
            
            ebit = net_income + income_tax_expense + interest_expense 
            market_value_of_equity = weighted_average_shares * price

            earning_yield = ebit / (market_value_of_equity + total_dept)
            roc = ebit / (working_capital + fixed_assets)
            combined_ratios.append({"EarningYield": earning_yield, "ROC": roc, "Price": price, "Market Cap": market_value_of_equity, "EBIT": ebit, "WC": working_capital, "Net Income": net_income})
            print(f"Ticker: {ticker}, Earning Yield: {earning_yield}, ROC: {roc}")
            tickers_with_data.append(ticker)


    final_stats_df = pd.DataFrame(combined_ratios, index=tickers_with_data)
    final_stats_val_df = final_stats_df.loc[tickers_with_data,:]
    final_stats_val_df["CombRank"] = final_stats_val_df["EarningYield"].rank(ascending=False,na_option='bottom')+final_stats_val_df["ROC"].rank(ascending=False,na_option='bottom')
    final_stats_val_df["MagicFormulaRank"] = final_stats_val_df["CombRank"].rank(method='first')
    value_stocks = final_stats_val_df.sort_values("MagicFormulaRank").iloc[:,[0,1,2]]
    value_stocks.to_excel(outputfile)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Magic formula analysis CLI tool")
    parser.add_argument("--api-key", required=True, help="API key for financial data")
    parser.add_argument("--country", required=True, help="Country for equity selection")
    parser.add_argument("--industry", required=True, help="Industry for equity selection")
    parser.add_argument("--output-file", required=True, help="Output file (XLSX)")
    parser.add_argument("--head", required=False, help="Calculate only the first x results")
    parser.add_argument("--market-cap", required=False, help="Market capitalization")
    try:
        return parser.parse_args()
    except:
        return None

def main():
    args = parse_arguments()
    
    api_key = api_key = getattr(args, 'api_key', API_KEY)
    country = getattr(args, 'country', COUNTRY)
    industry = getattr(args, 'industry', INDUSTRY)
    output_file = getattr(args, 'output_file', OUTPUTFILE)
    head = args.head if hasattr(args, 'head') and args.head is not None else HEAD
    market_cap = getattr(args, 'market_cap', MARKET_CAP)

    required_params = {'api_key': api_key, 'country': country, 'industry': industry, 'output_file': output_file, 'market_cap': market_cap}
    missing_params = [param for param, value in required_params.items() if value is None]
    if missing_params:
        raise ValueError(f"Missing the following parameters: {', '.join(missing_params)}")

    calc_magic_formula(api_key, head, country, market_cap, output_file)


if __name__ == "__main__":
    main()