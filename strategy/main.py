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
from time import sleep
import signal
import sys

from dotenv import load_dotenv
from api.ws import WebSocket

load_dotenv()

api_key = os.getenv("TESTNET_API_KEY")
api_secret = os.getenv("TESTNET_API_SECRET")
api_url = os.getenv("TESTNET_REST_BASE_URL")
ws_public_url = os.getenv("TESTNET_WS_PUBLIC_URL")

if __name__ == "__main__":
    ws = WebSocket(ws_public_url)
    print("Hello world - I am the stat bot :)")
    print(f"Ping: {ws.ping()}")

    ws.subscribe_to_kline()

    def signal_handler(sig, frame):
        print('You pressed Ctrl+C!')
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        sleep(1)
