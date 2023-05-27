import signal
import sys
import argparse
import logging

from config import Config
from strategy.test import Test
from strategy.execution import Execution
from api.rest_client import RestClient


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# 20230521 - Cointegrated pairs: 1000BTTUSDT,CHZUSDT
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sym1", help="Symbol 1", default="MATICUSDT")
    parser.add_argument("--sym2", help="Symbol 2", default="IMXUSDT")
    parser.add_argument("--logfile", help="Log filename", default="statbot_logs.txt")
    args = parser.parse_args()

    logname = args.logfile
    logging.basicConfig(
        filename=logname,
        filemode="w",
        format='%(asctime)s:%(msecs)d - %(name)s [%(levelname)s]: %(message)s',
        datefmt="%H:%M:%S",
        level=logging.DEBUG
    )
    logger = logging.getLogger('StatBot')

    symbol_1 = args.sym1
    symbol_2 = args.sym2 
    config = Config()

    logger.info(f"Running for symbol 1 ({symbol_1}) and symbol 2 ({symbol_2})")

    rc = RestClient(url=config.api_url, api_key=config.api_key, api_secret=config.api_secret)
    execution = Execution(config, rc, symbol_1, symbol_2)