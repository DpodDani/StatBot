import os
import signal
import sys
import json

from strategy.stat_arbitrage import StatArbitrage

from dotenv import load_dotenv

load_dotenv()


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

api_key = os.getenv("TESTNET_API_KEY")
api_secret = os.getenv("TESTNET_API_SECRET")
api_url = os.getenv("TESTNET_REST_BASE_URL")
ws_public_url = os.getenv("TESTNET_WS_PUBLIC_URL")

if __name__ == "__main__":
    sa = StatArbitrage(
        ws_public_url=ws_public_url,
        rest_api_url=api_url,
    )

    # 1) Get tradable symbols
    symbols = sa.get_tradeable_symbols()

    # 2.1) Get price history
    price_histories = sa.get_price_histories(symbols)

    # 2.2) Output prices to JSON file
    # filename = "1_price_histories.json"
    # if len(price_histories) > 0:
    #     print(f"Writing price histories to {filename}")
    #     with open(filename, "w") as fh:
    #         json.dump(price_histories, fh, indent=4)
    #     print(f"Saved prices to {filename} for {len(price_histories)} symbols")

