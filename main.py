import signal
import sys
import argparse

from config import Config
from strategy.test import Test


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

parser = argparse.ArgumentParser()
parser.add_argument("--sym1", help="Symbol 1", default="BATUSDT")
parser.add_argument("--sym2", help="Symbol 2", default="IMXUSDT")

args = parser.parse_args()
symbol_1 = args.sym1
symbol_2 = args.sym2


if __name__ == "__main__":
    config = Config()

    test = Test(config, symbol_1, symbol_2)
    test.run()