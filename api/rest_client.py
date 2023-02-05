import datetime
from time import sleep

from typing import Tuple, Union

import pybit.exceptions
from pybit import usdt_perpetual


def _get_start_time_in_seconds(interval: Union[int, str], limit: float):
    start = 0
    now = datetime.datetime.now()
    if interval == 60:
        start = now - datetime.timedelta(hours=limit)
        start = int(start.timestamp())
    elif interval == "D":
        start = now - datetime.timedelta(days=limit)
        start = int(start.timestamp())
    return start


class RestClient:
    def __init__(self, url: str, api_key: Union[str, None] = None, api_secret: Union[str, None] = None):
        self._url = url
        self._client = usdt_perpetual.HTTP(endpoint=self._url, api_key=api_key, api_secret=api_secret)

    def get_symbols(self, trading=None, maker_rebate=False) -> list:
        symbols = []
        resp = self._client.query_symbol()

        if "ret_msg" not in resp or "ret_code" not in resp:
            print("No 'ret_msg' or 'ret_code' found in response")
            return symbols

        if resp["ret_msg"] != "OK" or resp["ret_code"] != 0:
            print(f"Error in response: {resp}")
            return symbols

        symbols = list(filter(lambda x: x["quote_currency"] == "USDT", resp["result"]))

        if trading:
            symbols = list(filter(lambda x: x["status"] == "Trading", symbols))

        if maker_rebate:
            symbols = list(filter(lambda x: float(x["maker_fee"]) < 0, symbols))

        return symbols

    def get_price_history(self, symbol: str, interval: int, limit: int) -> Union[dict, None]:
        from_time = _get_start_time_in_seconds(interval, limit)
        prices = []
        try:
            sleep(0.1)
            prices = self._client.query_mark_price_kline(
                symbol=symbol,
                interval=interval,
                limit=limit,
                from_time=from_time,
            )
        except pybit.exceptions.InvalidRequestError:
            return None
        return prices

    def get_my_position(self, symbol: str):
        return self._client.my_position(symbol=symbol)