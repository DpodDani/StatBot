import pandas as pd
import matplotlib.pyplot as plt

from strategy.cointegration import (
    extract_close_prices,
    calculate_cointegration,
    calculate_spread,
    calculate_zscore
)


def plot_trends(symbol_data_1, symbol_data_2, window):
    # Extract prices
    prices_1 = extract_close_prices(symbol_data_1["data"])
    prices_2 = extract_close_prices(symbol_data_2["data"])

    # Calculate spread
    coint = calculate_cointegration(prices_1, prices_2)
    spread = calculate_spread(prices_1, prices_2, coint.hedge_ratio)

    # Calculate z-score
    zscore = calculate_zscore(spread, window)

    # Calculate percentage changes
    symbol_1 = symbol_data_1["symbol"]
    symbol_2 = symbol_data_2["symbol"]
    df = pd.DataFrame(columns=[symbol_1, symbol_2])

    df[symbol_1] = prices_1
    df[symbol_2] = prices_2

    # percentage changes compared to the 1st day
    df[f"{symbol_1}_pct"] = df[symbol_1] / prices_1[0]
    df[f"{symbol_2}_pct"] = df[symbol_2] / prices_2[0]

    series_1 = df[f"{symbol_1}_pct"].astype(float).values
    series_2 = df[f"{symbol_2}_pct"].astype(float).values

    backtest_filename = "3_backtest_file.csv"
    df_2 = pd.DataFrame()
    df_2[symbol_1] = prices_1
    df_2[symbol_2] = prices_2
    df_2["Spread"] = spread
    df_2["Z-Score"] = zscore
    df_2 = df_2[df_2["Z-Score"].notna()]
    df_2.to_csv(backtest_filename, index=False)
    print(f"Saved backtest data to {backtest_filename}")

    fig, axis = plt.subplots(3, figsize=(16, 8))
    fig.suptitle(f"Price and Spread - {symbol_1} vs {symbol_2}")
    axis[0].plot(series_1, label=symbol_1)
    axis[0].plot(series_2, label=symbol_2)
    axis[1].plot(spread, label="Spread")
    axis[2].plot(zscore, label="Z-score")

    axis[0].set_ylabel("Price")

    axis[0].legend()
    axis[1].legend()
    axis[2].legend()

    plt.show()


