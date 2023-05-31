import json

from strategy.stat_arbitrage import StatArbitrage
from strategy.cointegration import get_cointegration_pairs
from strategy.plot import plot_trends

class Test:
    def __init__(self, config, symbol_1: str, symbol_2: str):
        self._config = config
        self._symbol_1 = symbol_1
        self._symbol_2 = symbol_2

        self._prices_file = "1_price_histories.json"
        self._cointegrated_pairs_file = "2_cointegrated_pairs.csv"

    def run(self):
        sa = StatArbitrage(
            ws_public_url=self._config.ws_public_url,
            rest_api_url=self._config.api_url,
            price_interval=self._config.interval,
        )

        # 1) Get tradable symbols
        symbols = sa.get_tradeable_symbols()

        # 2.1) Get price history
        price_histories = sa.get_price_histories(symbols, self._config.limit)

        # 2.2) Output prices to JSON file
        if len(price_histories) > 0:
            print(f"Writing price histories to {self._prices_file}")
            with open(self._prices_file, "w") as fh:
                json.dump(price_histories, fh, indent=4)
            print(f"Saved prices to {self._prices_file} for {len(price_histories)} symbols")

        # 3) Find co-integrated pairs (and output to CSV file)
        with open(self._prices_file) as json_file:
            price_data = json.load(json_file)
            if len(price_data) > 0:
                print(f"Getting co-integrated pairs (and saving into {self._cointegrated_pairs_file})")
                coint_pairs_df = get_cointegration_pairs(price_data)
                coint_pairs_df.to_csv(self._cointegrated_pairs_file, index=False)

        # 4) Plot trends and save to file (for backtesting)
        self.plot()

    def plot(self):
        symbol_1 = self._symbol_1
        symbol_2 = self._symbol_2
        with open(self._prices_file) as json_file:
            price_data = json.load(json_file)
            if len(price_data) > 0:
                print(f"Plotting trend for ({symbol_1}) and ({symbol_2})")
                symbol_data_1 = {"symbol": symbol_1, "data": price_data[symbol_1]["result"]}
                symbol_data_2 = {"symbol": symbol_2, "data": price_data[symbol_2]["result"]}
                plot_trends(symbol_data_1, symbol_data_2, self._config.zscore_window)
