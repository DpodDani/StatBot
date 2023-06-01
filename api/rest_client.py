import datetime
from time import sleep

from typing import Union, List, Literal

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

    def get_price_history(self, symbol: str, interval: int, limit: int, from_time: int = -1) -> Union[dict, None]:
        if from_time == -1:
            from_time = _get_start_time_in_seconds(interval, limit)
        prices = {}
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
    
    def close_position(self, symbol, side, size, position_idx) -> bool:
        """Closing a position involves placing the opposite side

            So, if you have an open buy position, you want to place a sell order.
            More info on reduce_only here: https://www.bybit.com/en-US/help-center/bybitHC_Article?id=360039260574&language=en_US
        """
        resp = self._client.place_active_order(
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=size,
            time_in_force="GoodTillCancel",
            reduce_only=True,
            close_on_trigger=False,
            position_idx=position_idx
        )

        if resp["ret_code"] == 0:
            return True
        else:
            return False
        
    def cancel_all_active_orders(self, symbol: str) -> List[str]:
        resp = self._client.cancel_all_active_orders(symbol=symbol)
        if resp["ret_code"] != 0:
            return []
        else:
            return resp["result"]
        
    def set_leverage(self, symbol: str, buy_leverage: int = 1, sell_leverage: int = 1) -> bool:
        try:
            resp = self._client.cross_isolated_margin_switch(
                symbol=symbol,
                is_isolated=True,
                buy_leverage=buy_leverage,
                sell_leverage=sell_leverage,
            )
        except pybit.exceptions.InvalidRequestError as e:
            print("Failed to set leverage:", e)
            return False

        if resp["ret_code"] == 0:
            return True
        else:
            return False
        
    def place_limit_order(self, symbol: str, side: Literal["Buy", "Sell"], qty: float, price: float, stop_loss: float) -> dict:
        resp = self._client.place_active_order(
            symbol=symbol,
            side=side,
            order_type="Limit",
            qty=qty,
            price=price,
            time_in_force="PostOnly",
            reduce_only=False,
            close_on_trigger=False,
            stop_loss=stop_loss,
            position_idx=0,
        )

        if resp["ret_code"] == 0:
            print("Placed limit order:", resp)
        else:
            print("Failed to place limit order :(")

        return resp
        
    def place_market_order(self, symbol: str, side: Literal["Buy", "Sell"], qty: float, stop_loss: float) -> dict:
        resp = self._client.place_active_order(
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=False,
            close_on_trigger=False,
            stop_loss=stop_loss,
            position_idx=0,
        )

        if resp["ret_code"] == 0:
            print("Placed market order:", resp)
        else:
            print("Failed to place market order :(")
        
        return resp
    
    def get_public_trade_records(self, symbol: str, limit: int = 10) -> list:
        resp = self._client.public_trading_records(
            symbol=symbol,
            limit=limit, # number of trades to fetch
        )

        if resp["ret_code"] == 0:
            print("Got public trades")
            return resp["result"]
        else:
            print("Failed to get public trades :(")
            return []
        
    def get_active_order(self, symbol: str) -> list:
        resp = self._client.get_active_order(
            symbol=symbol,
            order_status="Created,New,PartiallyFilled,Active",
        )

        data = []
        if resp["ret_code"] == 0:
            if resp["result"]["data"]:
                data = resp["result"]["data"]
        return data
    
    def query_existing_order(self, symbol: str, order_id: str) -> dict:
        data = {}
        try:
            resp = self._client.query_active_order(
                symbol=symbol,
                order_id=order_id,
            )
        except pybit.exceptions.InvalidRequestError:
            print(f"Couldn't fetch order for symbol ({symbol}) and order_id ({order_id})")
        else:
            if resp["ret_code"] == 0 and resp["result"]["data"]:
                data = resp["result"]["data"][0]
        return data