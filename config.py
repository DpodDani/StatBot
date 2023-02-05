from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    # need to know level of accuracy required for price and quantity values
    # different number of decimal places can be used for the price and/or quantity for different tickers
    price_rounding_ticker_1: int = 0
    price_rounding_ticker_2: int = 0
    quantity_rounding_ticker_1: int = 0
    quantity_rounding_ticker_2: int = 0

    api_key: str = os.getenv("TESTNET_API_KEY", "")
    api_secret: str = os.getenv("TESTNET_API_SECRET", "")
    api_url: str = os.getenv("TESTNET_REST_BASE_URL", "")
    ws_public_url: str = os.getenv("TESTNET_WS_PUBLIC_URL", "")

    interval: int = int(os.getenv("TIME_RANGE", 60))
    zscore_window: int = int(os.getenv("Z_SCORE_LIMIT", 21))
    limit: int = int(os.getenv("HISTORY_DEPTH", 0))
