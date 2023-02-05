import config
from pybit import usdt_perpetual

from time import sleep

class Execution:
    def __init__(self, config: config.Config, symbol_1: str, symbol_2: str):
        self._config = config
        self._symbol_1 = symbol_1
        self._symbol_2 = symbol_2

    def run(self):
        ws = usdt_perpetual.WebSocket(
            test=True,
            ping_interval=2,  # the default is 30
            ping_timeout=1,  # the default is 10
            domain="bybit",  # the default is "bybit"
            retries=0
        )
    
        def handler(msg):
            print("Data 1", msg["data"][0])
            print("Data N", msg["data"][-1])

        ws.orderbook_25_stream(handler, self._symbol_1 or "BTCUSDT")
        ws.orderbook_25_stream(handler, self._symbol_2 or "BATUSDT")

        sleep(3)
