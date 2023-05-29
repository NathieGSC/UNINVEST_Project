import pandas as pd
import numpy as np
import yfinance as yf
from scipy.optimize import minimize

# Define the function to load the stock data
def load_stock_data(transactions, start_date, end_date):
    stock_symbols = list(set([transaction[0] for transaction in transactions]))
    stock_data = yf.download(stock_symbols, start=start_date, end=end_date)

    # Ensure the stock symbol is used as the column name
    if len(stock_symbols) == 1:
        stock_data = stock_data[['Adj Close']].rename(columns={'Adj Close': stock_symbols[0]})
    else:
        stock_data = stock_data['Adj Close']
    return stock_data

# Define the function that will load S&P500 data
def load_market_data(start_date, end_date):
    market_symbol = "^GSPC"  # S&P 500 index symbol
    market_data = yf.download(market_symbol, start=start_date, end=end_date)['Adj Close']
    return market_data

# Define the function that will load the 1 day closing price
def get_current_prices(stock_symbols):
    if isinstance(stock_symbols, pd.Index):
        stock_symbols = stock_symbols.to_list()
    stock_data = yf.download(stock_symbols, period="1d")["Adj Close"]
    if isinstance(stock_data, pd.Series):
        stock_data = stock_data.to_frame()
    return stock_data.iloc[-1]

# Define the function that will update the data for a specific time frame
def update_data(transactions, start_date='2022-01-01', end_date='2023-05-25'):
    stock_data = load_stock_data(transactions, start_date, end_date)

    if isinstance(stock_data, pd.Series):
        stock_data = stock_data.to_frame()

    daily_returns = stock_data.pct_change().dropna()

    market_daily_returns = load_market_data(start_date, end_date).pct_change().dropna()

    market_daily_returns = market_daily_returns.reindex(daily_returns.index).dropna()
    daily_returns = daily_returns.loc[market_daily_returns.index]

    return daily_returns, market_daily_returns

def calculate_portfolio_statistics(transactions):
    start_date = '2022-01-01'
    end_date = '2023-05-25'
    stock_data = load_stock_data(transactions, start_date, end_date)

    if isinstance(stock_data, pd.Series):
        stock_data = stock_data.to_frame()

    daily_returns = stock_data.pct_change().dropna()
    unique_stocks = daily_returns.columns

    invested_amounts = {}
    for stock, _, _, amount_invested in transactions:
        if stock in invested_amounts:
            invested_amounts[stock] += amount_invested
        else:
            invested_amounts[stock] = amount_invested

    total_invested = sum(invested_amounts.values())
    portfolio_weights = np.array([invested_amounts[stock] / total_invested for stock in unique_stocks])

    portfolio_daily_returns = np.dot(daily_returns.values, portfolio_weights.reshape(-1, 1))
    portfolio_return = np.mean(portfolio_daily_returns)
    portfolio_risk = np.std(portfolio_daily_returns)
    sharpe_ratio = portfolio_return / portfolio_risk

    market_daily_returns = load_market_data(start_date, end_date).pct_change().dropna()

    market_daily_returns = market_daily_returns.reindex(daily_returns.index).dropna()
    portfolio_daily_returns = pd.Series(portfolio_daily_returns.flatten(), index=daily_returns.index).loc[market_daily_returns.index]
    beta = np.cov(portfolio_daily_returns.squeeze(), market_daily_returns)[0][1] / np.var(market_daily_returns)

    return portfolio_return, portfolio_risk, sharpe_ratio, beta

def MDP(transactions):
    def weighted_std(weights, data):
        vol = np.nanstd(data, ddof=1, axis=0)
        numerator = np.dot(weights.T, vol)
        p = np.dot(data, weights.T)
        vol_p = p.std()
        return -numerator / vol_p
    
    def calculate_MDP_weights(returns: pd.DataFrame):
        bounds = [(0, 1) for _ in range(len(returns.columns))]
        cons = ({"type": "eq", "fun": lambda x: sum(x) - 1})
        x0 = np.zeros(len(returns.columns)) + 0.01
        sol = minimize(weighted_std, x0, method="SLSQP", args=returns,
                       constraints=cons, bounds=bounds)
        return sol.x
    
    daily_returns, _ = update_data(transactions)
    selected_stocks = list({transaction[0] for transaction in transactions})
    selected_returns = daily_returns[selected_stocks]
    mdp_weights = calculate_MDP_weights(selected_returns)
    current_prices = get_current_prices(selected_returns.columns)
    investments = calculate_investments(transactions, mdp_weights, current_prices)

    start_date = '2022-01-01'
    end_date = '2023-05-25'
    portfolio_weights = mdp_weights.reshape(-1, 1)
    portfolio_daily_returns = np.dot(daily_returns.values, portfolio_weights)
    portfolio_return = np.mean(portfolio_daily_returns)
    portfolio_risk = np.std(portfolio_daily_returns)
    sharpe_ratio = portfolio_return / portfolio_risk
    
    market_daily_returns = load_market_data(start_date, end_date).pct_change().dropna()
    market_daily_returns = market_daily_returns.reindex(daily_returns.index).dropna()
    portfolio_daily_returns = pd.Series(portfolio_daily_returns.flatten(), index=daily_returns.index).loc[market_daily_returns.index]
    beta = np.cov(portfolio_daily_returns.squeeze(), market_daily_returns)[0][1] / np.var(market_daily_returns)
    return mdp_weights, investments, portfolio_return, portfolio_risk, sharpe_ratio, beta


def EWP(transactions):
    def EWP_inner(returns: pd.DataFrame, selected_stocks):
        weight = np.zeros(len(returns.columns))
        for stock in selected_stocks:
            weight[returns.columns.get_loc(stock)] = 1 / len(selected_stocks)
        return weight

    daily_returns, _ = update_data(transactions)
    selected_stocks = list({transaction[0] for transaction in transactions})
    selected_returns = daily_returns[selected_stocks]
    ewp_weights = EWP_inner(selected_returns, selected_stocks)
    current_prices = get_current_prices(selected_returns.columns)
    investments = calculate_investments(transactions, ewp_weights, current_prices)

    start_date = '2022-01-01'
    end_date = '2023-05-25'
    portfolio_weights = ewp_weights.reshape(-1, 1)
    portfolio_daily_returns = np.dot(daily_returns.values, portfolio_weights)
    portfolio_return = np.mean(portfolio_daily_returns)
    portfolio_risk = np.std(portfolio_daily_returns)
    sharpe_ratio = portfolio_return / portfolio_risk
    
    market_daily_returns = load_market_data(start_date, end_date).pct_change().dropna()
    market_daily_returns = market_daily_returns.reindex(daily_returns.index).dropna()
    portfolio_daily_returns = pd.Series(portfolio_daily_returns.flatten(), index=daily_returns.index).loc[market_daily_returns.index]
    beta = np.cov(portfolio_daily_returns.squeeze(), market_daily_returns)[0][1] / np.var(market_daily_returns)
    return ewp_weights, investments, portfolio_return, portfolio_risk, sharpe_ratio, beta


def RWP(transactions):
    def RWP(returns: pd.DataFrame, selected_stocks):
        weight = returns[selected_stocks].sum() / returns[selected_stocks].sum().sum()
        return weight

    daily_returns, _ = update_data(transactions)
    selected_stocks = list({transaction[0] for transaction in transactions})
    selected_returns = daily_returns[selected_stocks]
    rwp_weights = RWP(selected_returns, selected_stocks)
    current_prices = get_current_prices(selected_returns.columns)
    investments = calculate_investments(transactions, rwp_weights, current_prices)

    start_date = '2022-01-01'
    end_date = '2023-05-25'
    portfolio_weights = rwp_weights.values.reshape(-1, 1)
    portfolio_daily_returns = np.dot(daily_returns.values, portfolio_weights)
    portfolio_return = np.mean(portfolio_daily_returns)
    portfolio_risk = np.std(portfolio_daily_returns)
    sharpe_ratio = portfolio_return / portfolio_risk
    
    market_daily_returns = load_market_data(start_date, end_date).pct_change().dropna()
    market_daily_returns = market_daily_returns.reindex(daily_returns.index).dropna()
    portfolio_daily_returns = pd.Series(portfolio_daily_returns.flatten(), index=daily_returns.index).loc[market_daily_returns.index]
    beta = np.cov(portfolio_daily_returns.squeeze(), market_daily_returns)[0][1] / np.var(market_daily_returns)

    return rwp_weights, investments, portfolio_return, portfolio_risk, sharpe_ratio, beta



def calculate_investments(transactions, weights, current_prices):
    total_investment = sum(transaction[3] for transaction in transactions)
    investments = {stock: weight * total_investment for stock, weight in zip(current_prices.index, weights)}

    return investments


