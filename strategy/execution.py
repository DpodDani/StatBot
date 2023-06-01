from dataclasses import dataclass
from typing import Union, List, Literal, Tuple, Optional
import config, json

from pybit import usdt_perpetual
from time import sleep
import datetime
import logging

from strategy.cointegration import extract_close_prices
from api.rest_client import RestClient

from statistics import mean

from strategy.cointegration import calculate_cointegration, calculate_spread, calculate_zscore

logger = logging.getLogger(__name__)

@dataclass
class TradeDetails:
    symbol: str
    order_price: float
    stop_loss: float
    quantity: float

@dataclass
class PositionInfo:
    order_price: float
    size: float
    side: str
    idx: int

class Execution:
    def __init__(
        self,
        config: config.Config,
        rest_client: RestClient,
        symbol_1: str,
        symbol_2: str,
        state_file: Optional[str] = None,
    ):
        self._config = config
        self._rc = rest_client
        self._symbol_1 = symbol_1
        self._symbol_2 = symbol_2
        self._state_file = state_file

    def get_trade_details(self, orderbook: list, direction: str = "Long", capital: float = 0) -> Union[TradeDetails, None]:
        
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
                positions.append(
                    PositionInfo(
                        order_price=pos["entry_price"],
                        size=pos["size"],
                        side=pos["side"],
                        idx=pos["position_idx"]
                    )
                )

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
            if res:
                logger.warning(f"Cancelled these active orders for symbol ({symbol}): {', '.join(res)}")
            else:
                logger.info(f"No active orders cancelled for {symbol}")

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

    def place_order(self, trade_details: TradeDetails, direction: Literal["Long", "Short"]) -> dict:
        side = "Buy" if direction == "Long" else "Sell"

        if self._config.limit_order:
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
    def _get_order_book(ticker: str) -> list:
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

    def initalise_order_execution(self, ticker: str, direction: Literal["Long", "Short"], capital: float) -> str:
        orderbook = Execution._get_order_book(ticker)
        trade_details = self.get_trade_details(orderbook, direction, capital)

        if not trade_details:
            print("Orderbook is empty, so cannot initialise order exeuction")
            return ""

        order = self.place_order(trade_details, direction)
        if "result" in order:
            if "order_id" in order["result"]:
                return order["result"]["order_id"]
            
        print("Did not place order :(")
        return ""
    
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
    
    def get_latest_zscore(self, ticker_1: str, ticker_2: str) -> Tuple[float, bool]:
        orderbook_1 = Execution._get_order_book(ticker_1)
        trade_details_1 = self.get_trade_details(orderbook_1)

        orderbook_2 = Execution._get_order_book(ticker_2)
        trade_details_2 = self.get_trade_details(orderbook_2)

        if not trade_details_1 or not trade_details_2:
            raise Exception("Need trade details for both tickers!")

        series_1, series_2 = self.get_latest_klines(ticker_1, ticker_2)
        
        # Replace latest kline (close) price with latest orderbook "mid-price"
        series_1[-1] = trade_details_1.order_price
        series_2[-1] = trade_details_2.order_price

        # Deviating a little from tutorial, because we do care
        # whether pairs are still cointegrated at this point
        cointegrated, zscore_list = self.calculate_metrics(series_1, series_2)
        return (zscore_list[-1], cointegrated)
    
    def open_positions_found(self, ticker: str):
        positions = self.get_position_info(ticker)
        if len(positions) > 0:
            return True
        else:
            return False
        
    def active_order_found(self, ticker: str):
        active_order = self._rc.get_active_order(ticker)
        if len(active_order) > 0:
            return True
        else:
            return False
        
    def get_open_position(self, ticker: str, direction: Literal["Long", "Short"] = "Long") -> Tuple[float, float]:
        positions = self.get_position_info(ticker)
        side = "Buy" if direction == "Long" else "Sell"
        for position in positions:
            if position.side == side:
                return (position.order_price, position.size)
        return (0, 0)
    
    def get_active_position(self, ticker: str):
        active_order = self._rc.get_active_order(ticker)
        if len(active_order) > 0:
            return (active_order[0]["price"], active_order[0]["qty"])
        return (0, 0)

    def query_existing_order(self, ticker: str, order_id: str) -> Union[Tuple[float, float, str], None]:
        existing_order = self._rc.query_existing_order(ticker, order_id)
        if existing_order:
            return (
                existing_order["price"],
                existing_order["qty"],
                existing_order["order_status"],
            )
        return None
    
    def check_order(
        self,
        ticker: str,
        order_id: str,
        remaining_capital: float,
        direction: Literal["Long", "Short"] = "Long"
    ):
        orderbook = self._get_order_book(ticker)
        trade_details = self.get_trade_details(orderbook)

        # Get latest price
        mid_price = 0
        if trade_details:
            mid_price = trade_details.order_price

        # Get latest trade details
        existing_order = self.query_existing_order(ticker, order_id)
        
        if not existing_order:
            return None

        order_price, quantity, order_status = existing_order

        # Get open position
        pos_price, pos_size = self.get_open_position(ticker, direction)

        # Get active positions
        active_price, active_quantity = self.get_active_position(ticker)

        # TODO: Understand what the meaning of this if statement is!
        # Determine if trade is complete --> if it is, stop placing orders
        if pos_size >= remaining_capital:
            return "Trade complete" # TODO: Make ENUM!

        # Determine action needed --> if positions filled, buy more
        if order_status == "Filled":
            return "Position filled" # TODO: Make ENUM!
        
        # Determine if order active --> if active, do nothing
        if order_status in ["Created", "New"]:
            return "Order active"
        
        # Determine if partially filled --> if partially filled, do nothing
        if order_status == "PartiallyFilled":
            return "Partial fill"
        
        # Determine if order failed --> if failed, try place order again
        if order_status in ["Cancelled", "Rejected", "PendingCancel"]:
            return "Try again"
        
    def manage_new_trades(
        self, killswitch: int,  ticker_1: str, ticker_2: str, total_capital: int = 2000
    ) -> int:
        zscore, cointegrated = self.get_latest_zscore(ticker_1, ticker_2)
        logger.info(f"Z-score: {zscore} :: cointegrated? {cointegrated}")

        # if not cointegrated:
        #     logger.error(f"Pairs ({ticker_1}) and ({ticker_2}) are not cointegrated")
        #     return 1

        hot = False
        logger.info(f"Signal trigger threshold: {self._config.signal_trigger_threshold}")
        if abs(zscore) > self._config.signal_trigger_threshold:
            hot = True
            logger.info("-- Trade status HOT --")
            logger.info("Placing and monitoring existing trades")
        else:
            logger.info("-- Trade status NOT HOT --")

        # Place and monitor trades
        if hot and killswitch == 0:
            # Get trade history for liquidity
            avg_qty_1, last_price_1 = self.get_trade_liquidity(ticker_1)
            avg_qty_2, last_price_2 = self.get_trade_liquidity(ticker_2)

            # If zscore is +ve, then we want to go long on ticker 2 and short of ticker 1
            # Vice versa if zscore is -ve
            # As per our backtesting using Jupyter notebook
            long_ticker = ticker_2 if zscore > 0 else ticker_1
            avg_liquidity_long = avg_qty_2 if zscore > 0 else avg_qty_1
            last_price_long = last_price_2 if zscore > 0 else last_price_1

            short_ticker = ticker_1 if zscore > 0 else ticker_2
            avg_liquidity_short = avg_qty_1 if zscore > 0 else avg_qty_2
            last_price_short = last_price_1 if zscore > 0 else last_price_2

            # Fill targets

            # Currency that I use on exchange platform (eg. GBP)
            capital_long = total_capital * 0.5
            capital_short = total_capital * 0.5

            # All in units of USDT
            long_initial_fill_target = avg_liquidity_long * last_price_long
            short_initial_fill_target = avg_liquidity_short * last_price_short

            logger.info(f"[Long] average liquidity: {avg_liquidity_long} -- last price: {last_price_long}")
            logger.info(f"[Short] average liquidity: {avg_liquidity_short} -- last price: {last_price_short}")

            # The idea is to use the same capital for both symbols on the initial (limit) trades
            # Once both those trades are filled, we do another round of initial capital injection
            # for both limit orders
            initial_capital_injection = min(long_initial_fill_target, short_initial_fill_target)

            if self._config.limit_order:
                # if initial capital injection is more than we want to trade, then
                # override initial captial
                if initial_capital_injection > capital_long:
                    initial_capital = capital_long
                else:
                    initial_capital = initial_capital_injection
            else: # market order
                initial_capital = capital_long

            # Set remaining capital
            long_remaining_capital = capital_long
            short_remaining_capital = capital_short

            logger.info(f"[Long] remaining capital: {long_remaining_capital}")
            logger.info(f"[Short] remaining capital: {short_remaining_capital}")
            logger.info(f"Initial capital: {initial_capital}")

            # Trade until filled or signal is false
            long_order_status = ""
            short_order_status = ""
            long_count = 0
            short_count = 0

            while killswitch == 0:
                # place long order
                if long_count == 0:
                    long_order_id = self.initalise_order_execution(long_ticker, "Long", initial_capital)
                    long_count = 1 if long_order_id != "" else 0
                    long_remaining_capital = long_remaining_capital - initial_capital

                    logger.info(f"[Long] placed order for {long_ticker}: {long_order_id}")

                # place long order
                if short_count == 0:
                    short_order_id = self.initalise_order_execution(short_ticker, "Short", initial_capital)
                    short_count = 1 if short_order_id != "" else 0
                    short_remaining_capital = short_remaining_capital - initial_capital

                    logger.info(f"[Short] placed order for {short_ticker}: {short_order_id}")

                if not self._config.limit_order:
                    killswitch = 1

                sleep(3) # give time for orders to register
        
        return -1
            