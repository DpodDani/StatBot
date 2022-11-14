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
    print(f"Symbols: {rc.get_symbols()}")
    print(f"Tradeable symbols with maker rebate: {rc.get_symbols(True)}")
