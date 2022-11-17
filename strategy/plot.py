from strategy.cointegration import (
    extract_close_prices,
    calculate_cointegration,
    calculate_spread,
    calculate_zscore
)


def plot_trends(symbol_1_data, symbol_2_data, window):
    prices_1 = extract_close_prices(symbol_1_data)
    prices_2 = extract_close_prices(symbol_2_data)

    coint = calculate_cointegration(prices_1, prices_2)
    spread = calculate_spread(prices_1, prices_2, coint.hedge_ratio)
    zscore = calculate_zscore(spread, window)

    print(zscore)

