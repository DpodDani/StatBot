from dataclasses import dataclass
from typing import Union
import config

from pybit import usdt_perpetual
from time import sleep

from strategy.cointegration import extract_close_prices
from api.rest_client import RestClient

@dataclass
class TradeDetails:
    symbol: str
    order_price: float
    stop_loss: float
    quantity: float

@dataclass
class PositionInfo:
    size: float
    side: str

class Execution:
    def __init__(self, config: config.Config, rest_client: RestClient, symbol_1: str, symbol_2: str):
        self._config = config
        self._rc = rest_client
        self._symbol_1 = symbol_1
        self._symbol_2 = symbol_2

    def get_trade_details(self, orderbook: list, direction: str = "Long", capital=0) -> Union[TradeDetails, None]:
        
        # Set calculation and output variables
        price_rounding = 20
        quantity_rounding = 20
        order_price = 0
        quantity = 0
        stop_loss = 0
        bid_items_list = [] # bid refers to highest price buyer will pay
        ask_items_list = [] # ask refers to lowest price at which seller will sell

        # Get prices, stop loss and quantity
        if orderbook:
            symbol = orderbook[0]["symbol"]

            # Set price rounding
            if symbol == self._symbol_1:
                price_rounding = self._config.price_rounding_ticker_1
                quantity_rounding = self._config.quantity_rounding_ticker_1
            else:
                price_rounding = self._config.price_rounding_ticker_2
                quantity_rounding = self._config.quantity_rounding_ticker_2

            # Organise prices
            for level in orderbook:
                price = float(level["price"])
                if level["side"] == "Buy":
                    bid_items_list.append(price)
                else:
                    ask_items_list.append(price)

            # Calculate price, size, stop loss and average liquidity
            if len(ask_items_list) > 0 and len(bid_items_list) > 0:

                # Sort list - to get the best price
                ask_items_list.sort() # get lowest ask price at beginning of list
                bid_items_list.sort()
                bid_items_list.reverse() # get highest bid price at beginning of list

                # Get nearest ask, nearest bid and orderbook spread
                nearest_ask = ask_items_list[0]
                nearest_bid = bid_items_list[0]

                # Calculate order price and hard stop loss
                if direction == "Long":
                    # setting this to nearest_bid increases changes of order NOT being cancelled,
                    # and at the same time the order not being filled
                    order_price = nearest_bid # can also be (nearest_bid + nearest_ask) / 2
                else: # short position
                    order_price = nearest_ask
                stop_loss = round(order_price * (1 - self._config.stop_loss_fail_safe), price_rounding)

                # Calculate quantity
                quantity = round(capital / order_price, quantity_rounding)
        
            return TradeDetails(symbol, order_price, stop_loss, quantity)
        return None

    def get_position_info(self, symbol: str):
        positions = []

        position = self._rc.get_my_position(symbol)

        if not "ret_msg" in position.keys() or not position["ret_msg"] == "OK":
            return positions
        
        if not len(position["result"]) > 0:
            return positions
        
        # expect max. 2 positions - one for buy and one for sell
        for pos in position["result"]:
            if pos["size"] > 0:
                positions.append(PositionInfo(size=pos["size"], side=pos["side"]))

        return positions

    def run(self):
        ws = usdt_perpetual.WebSocket(
            test=True,
            ping_interval=2,  # the default is 30
            ping_timeout=1,  # the default is 10
            domain="bybit",  # the default is "bybit"
            retries=0
        )
    
        def handler(msg):
            trade_details = self.get_trade_details(orderbook=msg["data"], direction="Long", capital=1000)
            print(trade_details)
            print(msg["data"][0])

        ws.orderbook_25_stream(handler, self._symbol_1 or "BTCUSDT")
        ws.orderbook_25_stream(handler, self._symbol_2 or "BATUSDT")

        sleep(5)
