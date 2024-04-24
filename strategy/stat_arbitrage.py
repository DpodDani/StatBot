# Game plan
# 1. Get trade-able symbols
# 2. Get price history
# 3. Perform co-integration calculation
# 4. Analyse findings using spread and z-score
#   4.1 - plot charts
#   4.2 - how many times does z-score cross 0 line
#   4.3 - filter for best co-integrated pairs
# 5. Backtest

import sys, time

from api.ws import WebSocket
from api.rest_client import RestClient


class StatArbitrage:
    def __init__(self,
                 ws_public_url: str,
                 rest_api_url: str,
                 price_interval: int):
        self._ws = WebSocket(ws_public_url)
        self._rc = RestClient(rest_api_url)
        self._interval = price_interval
        print(f"Ping: {self._ws.ping()}")

    def get_tradeable_symbols(self):
        symbols = self._rc.get_symbols(trading=True)
        if len(symbols) < 0:
            print("No tradeable symbols found. Exiting.")
            sys.exit(0)
        else:
            print(f"Fetched {len(symbols)} symbols")
        return symbols

    def get_price_histories(self, symbols, limit):
        price_histories = {}
        success = 0
        failures = 0
        skipped = 0
        for symbol in symbols:
            name = symbol["name"]
            prices = self._rc.get_price_history(
                symbol=name,
                interval=self._interval,
                limit=limit)

            if not prices:
                failures += 1
            else:
                if len(prices["result"]) < limit:
                    skipped += 1
                else:
                    price_histories[name] = prices
                    success += 1

            time.sleep(0.1) # 100ms

            if (success + failures + skipped) % 20 == 0:
                print(f"Successes: {success}. Failures: {failures}. Skipped: {skipped}")

        return price_histories
