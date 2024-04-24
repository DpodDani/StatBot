import websocket, json
from pybit import usdt_perpetual


class WebSocket:
    def __init__(self, url: str):
        self.url = url
        self._ws = websocket.WebSocket()
        self._ws.connect(self.url)
        self._ws_usdt_perpetual = usdt_perpetual.WebSocket(
            test=True,
            ping_interval=2,  # the default is 30
            ping_timeout=1,  # the default is 10
            domain="bybit",  # the default is "bybit"
            retries=0
        )
        print("Connected WebSocket")

    def ping(self):
        self._ws.send('{"op":"ping"}')
        return self._ws.recv()