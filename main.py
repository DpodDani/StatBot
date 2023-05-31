import signal
import sys
import argparse
import logging

from time import sleep
from config import Config
from strategy.test import Test
from strategy.execution import Execution
from api.rest_client import RestClient


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# 20230521 - Cointegrated pairs: 1000BTTUSDT,CHZUSDT
# 20230531 - Cointegrated pairs: SFPUSDT, USDCUSDT
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sym1", help="Symbol 1", default="MATICUSDT")
    parser.add_argument("--sym2", help="Symbol 2", default="IMXUSDT")
    parser.add_argument("--logfile", help="Log filename", default="statbot_logs.txt")
    parser.add_argument("--generate", help="Generate cointegration data", default=False, action="store_true")
    parser.add_argument("--plot", help="Plot graph", default=False, action="store_true")
    args = parser.parse_args()

    config = Config()
    symbol_1 = args.sym1
    symbol_2 = args.sym2 

    if args.generate:
        print("Generating cointegration data...")
        t = Test(config, symbol_1, symbol_2)
        t.run()
        sys.exit(0)

    if args.plot:
        print(f"Plotting graph for ({symbol_1}) and ({symbol_2})...")
        t = Test(config, symbol_1, symbol_2)
        t.plot()
        sys.exit(0)

    logname = args.logfile
    logging.basicConfig(
        filename=logname,
        filemode="w",
        format='%(asctime)s:%(msecs)d - %(name)s [%(levelname)s]: %(message)s',
        datefmt="%H:%M:%S",
        level=logging.INFO # set to DEBUG to see API logs too!
    )
    logger = logging.getLogger('StatBot')

    logger.info(f"Running for symbol 1 ({symbol_1}) and symbol 2 ({symbol_2})")

    rc = RestClient(url=config.api_url, api_key=config.api_key, api_secret=config.api_secret)
    execution = Execution(config, rc, symbol_1, symbol_2)

    logger.info("Setting leverage for both symbols")
    execution.set_leverage(symbol_1)
    execution.set_leverage(symbol_2)
    
    killswitch = 0

    logger.info("Seeking trades...")
    while True:
        sleep(3) # avoid breaching API rate limit

        # Check if open trades already exist
        symbol_1_open = execution.open_positions_found(symbol_1)
        symbol_2_open = execution.open_positions_found(symbol_2)

        # Check if active positions exist
        symbol_1_active = execution.active_order_found(symbol_1)
        symbol_2_active = execution.active_order_found(symbol_2)

        checks = [symbol_1_open, symbol_1_active, symbol_2_open, symbol_2_active]
        logger.info(f"Checks: {checks}")

        # Can only look to manage new trades if all of the above checks are false
        if not any(checks) and killswitch == 0:
            logger.info("Managing new trades...")
            killswitch = execution.manage_new_trades(killswitch, symbol_1, symbol_2)

        # Close all active orders and positions
        if killswitch == 2:
            logger.info("Closing existing trades...")
            killswitch = execution.close_all_positions(killswitch)
            sleep(5) # bot waits before placing new trades

        break