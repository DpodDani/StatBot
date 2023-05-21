import signal
import sys
import argparse

from config import Config
from strategy.test import Test
from strategy.execution import Execution
from api.rest_client import RestClient


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

# 20230521 - Cointegrated pairs: 1000BTTUSDT,CHZUSDT
parser = argparse.ArgumentParser()
parser.add_argument("--sym1", help="Symbol 1", default="MATICUSDT")
parser.add_argument("--sym2", help="Symbol 2", default="IMXUSDT")

args = parser.parse_args()
symbol_1 = args.sym1
symbol_2 = args.sym2


if __name__ == "__main__":
    config = Config()

    print(f"Running for symbol 1 ({symbol_1}) and symbol 2 ({symbol_2})")

    rc = RestClient(url=config.api_url, api_key=config.api_key, api_secret=config.api_secret)

    # test = Test(config, symbol_1, symbol_2)
    # test.run()

    # import sys
    # sys.exit(0)

    execution = Execution(config, rc, symbol_1, symbol_2)
    # price_klines = execution.get_price_klines(symbol_1)
    # print(f"Price klines for {symbol_1}: {price_klines}")

    # latest_klines_1, latest_klines_2 = execution.get_latest_klines(symbol_1, symbol_2)
    # print(f"Latest klines for {symbol_1}: {latest_klines_1}")
    # print(f"Latest klines for {symbol_2}: {latest_klines_2}")

    # trade_liquidity = execution.get_trade_liquidity(symbol_1)
    # print(f"Trade liquidity for {symbol_1}:", trade_liquidity)

    # latest_zscore = execution.get_latest_zscore(symbol_1, symbol_2)
    # if latest_zscore:
    #     print(f"Latest Z-score:", latest_zscore[0], latest_zscore[1])
    # else:
    #     print(f"Couldn't get latest zscore for {symbol_1} and {symbol_2}")

    # print(f"Found open position for ({symbol_1}):", execution.open_positions_found(symbol_1))
    # print(f"Found active order for ({symbol_1}):", execution.active_order_found(symbol_1))

    print(f"Found active position for ({symbol_1}):", execution.get_active_position(symbol_1))
    print(f"Found active position for ({symbol_2}):", execution.get_active_position(symbol_2))