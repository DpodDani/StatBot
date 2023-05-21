from dataclasses import dataclass
from typing import Union, List, Literal, Tuple
import config

from pybit import usdt_perpetual
from time import sleep
import datetime

from strategy.cointegration import extract_close_prices
from api.rest_client import RestClient

from statistics import mean

from strategy.cointegration import calculate_cointegration, calculate_spread, calculate_zscore

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
    idx: int

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
                    stop_loss = round(order_price * (1 - self._config.stop_loss_fail_safe), price_rounding)
                else: # short position
                    order_price = nearest_ask
                    stop_loss = round(order_price * (1 + self._config.stop_loss_fail_safe), price_rounding)
                

                # Calculate quantity
                quantity = round(capital / order_price, quantity_rounding) if capital > 0 else 0
        
            return TradeDetails(symbol, order_price, stop_loss, quantity)
        return None

    def get_position_info(self, symbol: str) -> List[PositionInfo]:
        positions = []

        position = self._rc.get_my_position(symbol)

        if not "ret_msg" in position.keys() or not position["ret_msg"] == "OK":
            return positions
        
        if not len(position["result"]) > 0:
            return positions
        
        # expect max. 2 positions - one for buy and one for sell
        # for this strategy, we will only get 1 result, because we are either buying or selling a symbol, not both!
        for pos in position["result"]:
            if pos["size"] > 0:
                positions.append(PositionInfo(size=pos["size"], side=pos["side"], idx=pos["position_idx"]))

        return positions

    def place_marker_close_order(self, symbol, position, size, position_idx):
        return self._rc.close_position(symbol, position, size, position_idx)

    # cancel all active orders
    def close_all_positions(self, kill_switch: int):
        def reverse_side(side):
            if side == "Buy":
                return "Sell"
            else:
                return "Buy"

        for symbol in [self._symbol_1, self._symbol_2]:
            res = self._rc.cancel_all_active_orders(symbol)
            print(f"Result from cancelling all active orders for symbol ({symbol}):", res)

            pos_info = self.get_position_info(symbol)
            if len(pos_info) < 1:
                print(f"Found no position info for symbol: {symbol}. Skipping")
                continue

            res = self.place_marker_close_order(symbol, reverse_side(pos_info[0].side), pos_info[0].size, pos_info[0].idx)
            print(f"Result from closing positions for symbol {symbol}:", res)

        kill_switch = 0 # indicates that we've closed all our positions and we're ready to start looking to open again
        return kill_switch

    def set_leverage(self, ticker):
        return self._rc.set_leverage(ticker)

    def place_order(self, trade_details: TradeDetails, direction: Literal["Long", "Short"], limit_order: bool = True) -> dict:
        side = "Buy" if direction == "Long" else "Sell"

        if limit_order:
            result = self._rc.place_limit_order(
                symbol=trade_details.symbol,
                side=side,
                qty=trade_details.quantity,
                price=trade_details.order_price,
                stop_loss=trade_details.stop_loss,
            )
        else:
            result = self._rc.place_market_order(
                symbol=trade_details.symbol,
                side=side,
                qty=trade_details.quantity,
                stop_loss=trade_details.stop_loss,
            )

        return result

    @staticmethod
    def _get_order_book(ticker) -> list:
        ws = usdt_perpetual.WebSocket(
            test=True,
            ping_interval=2,  # the default is 30
            ping_timeout=1,  # the default is 10
            domain="bybit",  # the default is "bybit"
            retries=0
        )

        orderbooks: List[list] = []
        done = False
        def handler(msg):
            nonlocal done
            orderbooks.append(msg["data"])
            done = True

        ws.orderbook_25_stream(handler, ticker)

        while not done:
            sleep(0.1)

        return orderbooks[0]

    def initalise_order_execution(self, ticker: str, direction: Literal["Long", "Short"], capital: int) -> int:
        orderbook = Execution._get_order_book(ticker)
        trade_details = self.get_trade_details(orderbook, direction, capital)

        if not trade_details:
            print("Orderbook is empty, so cannot initialise order exeuction")
            return -1

        order = self.place_order(trade_details, direction)
        if "result" in order:
            if "order_id" in order["result"]:
                return int(order["results"]["order_id"])
            
        print("Did not place order :(")
        return -1
    
    def _get_timestamps(self) -> Tuple[int, int, int]:
        timeframe = self._config.interval
        history_depth = self._config.limit

        start_time = next_time = 0
        now = datetime.datetime.now()

        if timeframe == 60: # timeframe of 1 hour
            start_time = now - datetime.timedelta(hours=history_depth)
            next_time = now + datetime.timedelta(minutes=history_depth)
        elif timeframe == "D": # timeframe of 1 day
            start_time = now - datetime.timedelta(days=history_depth)
            next_time = now + datetime.timedelta(hours=history_depth)
        else:
            return (0, 0, 0)

        start_time_seconds = int(start_time.timestamp())
        next_time_seconds = int(next_time.timestamp())
        now_seconds = int(now.timestamp())

        return (
            start_time_seconds,
            now_seconds,
            next_time_seconds,
        )

    # The K-line consists of the opening price, closing price, the highest price,
    # and lowest price within a certain period of time
    def get_price_klines(self, ticker: str) -> list:
        kline_limit = self._config.limit

        # Get prices
        time_start_seconds, _, _ = self._get_timestamps()
        prices = self._rc.get_price_history(
            ticker,
            interval=self._config.interval,
            limit=kline_limit,
            from_time=time_start_seconds,
        )

        sleep(0.1) # manage API calls
        
        # prices is None if API error encountered
        if prices and len(prices["result"]) == kline_limit:
            return prices["result"]

        return []
    
    def get_latest_klines(self, symbol_1: str, symbol_2: str) -> Tuple[list, list]:
        series_1 = []
        series_2 = []

        prices_1 = self.get_price_klines(symbol_1)
        prices_2 = self.get_price_klines(symbol_2)

        if len(prices_1) > 0:
            series_1 = extract_close_prices(prices_1)

        if len(prices_2) > 0:
            series_2 = extract_close_prices(prices_2)

        return (series_1, series_2)

    def get_trade_liquidity(self, ticker: str) -> Tuple[float, float]:
        trades = self._rc.get_public_trade_records(ticker, limit=50)

        if not trades:
            return (0,0)
        
        quantity_avg = mean([trade["qty"] for trade in trades])

        return (quantity_avg, trades[0]["price"])
    
    def calculate_metrics(self, series_1, series_2) -> Tuple[bool, list]:
        coint = calculate_cointegration(series_1, series_2)
        if coint:
            spread = calculate_spread(series_1, series_2, coint.hedge_ratio)
            zscore = calculate_zscore(spread, self._config.zscore_window)
            return (coint.cointegrated, zscore)
        return (False, [])