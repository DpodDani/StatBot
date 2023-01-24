import os
import signal
import sys
import json

from strategy.stat_arbitrage import StatArbitrage
from strategy.cointegration import get_cointegration_pairs
from strategy.plot import plot_trends

from dotenv import load_dotenv

load_dotenv()


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

api_key = os.getenv("TESTNET_API_KEY", "")
api_secret = os.getenv("TESTNET_API_SECRET", "")
api_url = os.getenv("TESTNET_REST_BASE_URL", "")
ws_public_url = os.getenv("TESTNET_WS_PUBLIC_URL", "")

interval = int(os.getenv("TIME_RANGE", 60))
zscore_window = int(os.getenv("Z_SCORE_LIMIT", 21))
limit = int(os.getenv("HISTORY_DEPTH", 0))

if __name__ == "__main__":
    sa = StatArbitrage(
        ws_public_url=ws_public_url,
        rest_api_url=api_url,
        price_interval=interval,
    )

    # 1) Get tradable symbols
    symbols = sa.get_tradeable_symbols()

    # 2.1) Get price history
    price_histories = sa.get_price_histories(symbols, limit)

    # 2.2) Output prices to JSON file
    filename = "1_price_histories.json"
    if len(price_histories) > 0:
        print(f"Writing price histories to {filename}")
        with open(filename, "w") as fh:
            json.dump(price_histories, fh, indent=4)
        print(f"Saved prices to {filename} for {len(price_histories)} symbols")

    # 3) Find co-integrated pairs (and output to CSV file)
    coint_pairs_filename = "2_cointegrated_pairs.csv"
    with open(filename) as json_file:
        price_data = json.load(json_file)
        if len(price_data) > 0:
            print(f"Getting co-integrated pairs (and saving into {coint_pairs_filename})")
            coint_pairs_df = get_cointegration_pairs(price_data)
            coint_pairs_df.to_csv(coint_pairs_filename, index=False)

    # 4) Plot trends and save to file (for backtesting)
    symbol_1 = "BLZUSDT"
    symbol_2 = "SLPUSDT"
    with open(filename) as json_file:
        price_data = json.load(json_file)
        if len(price_data) > 0:
            print(f"Plotting trend for ({symbol_1}) and ({symbol_2})")
            symbol_data_1 = {"symbol": symbol_1, "data": price_data[symbol_1]["result"]}
            symbol_data_2 = {"symbol": symbol_2, "data": price_data[symbol_2]["result"]}
            plot_trends(symbol_data_1, symbol_data_2, zscore_window)
