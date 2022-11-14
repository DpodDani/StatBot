# Game plan
# 1. Get trade-able symbols
# 2. Get price history
# 3. Perform co-integration calculation
# 4. Analyse findings using spread and z-score
#   4.1 - plot charts
#   4.2 - how many times does z-score cross 0 line
#   4.3 - filter for best co-integrated pairs
# 5. Backtest

import os
import signal
import sys
import json

from dotenv import load_dotenv
from api.ws import WebSocket
from api.rest_client import RestClient

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
    ws = WebSocket(ws_public_url)
    rc = RestClient(api_url)
    print(f"Ping: {ws.ping()}")

    # 1. Get tradable symbols
    symbols = rc.get_symbols(trading=True)
    if len(symbols) < 0:
        print("No tradeable symbols found. Exiting.")
        sys.exit(0)
    else:
        print(f"Fetched {len(symbols)} symbols")

    # 2. Get price history
    price_histories = {}
    success = 0
    failures = 0
    for symbol in symbols:
        name = symbol["name"]
        if "BTC" in name:
            print(f"Found Bitcoin: {name}")
        prices, error = rc.get_price_history(
            symbol=name,
            interval=60,
            limit=200)

        if error:
            failures += 1
        else:
            price_histories[name] = prices
            success += 1

        if (success + failures) % 20 == 0:
            print(f"Successes: {success}. Failures: {failures}")

    # 3. Output prices to JSON file
    history_count = len(price_histories)
    if history_count > 0:
        filename = "1_price_histories.json"
        print(f"Writing price histories to {filename}")
        with open(filename, "w") as fh:
            json.dump(price_histories, fh, indent=4)
        print(f"Saved prices to {filename} for {history_count} symbols")

