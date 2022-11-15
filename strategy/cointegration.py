import math
import statsmodels.api as sm
import pandas as pd
import numpy as np

from statsmodels.tsa.stattools import coint
from dataclasses import dataclass

def _form_key(symbol1, symbol2):
    return f"{symbol1}-{symbol2}"


def _extract_close_prices(prices: dict):
    close_prices = []
    for price in prices:
        close_price = price["close"]
        if math.isnan(close_price):
            return []
        close_prices.append(close_price)
    print("Close prices:", close_prices)
    return close_prices


# TODO: Complete this function!
def get_cointegration_pairs(price_data: dict):
    pairs = {}
    for symbol, data in price_data.items():
        for symbol2, data2 in price_data.items():
            if symbol == symbol2:
                continue
            if _form_key(symbol, symbol2) in pairs \
                    or _form_key(symbol2, symbol) in pairs:
                # not using continue cause 180x180 is BIG!
                break

            series_1 = _extract_close_prices(data["result"])
            series_2 = _extract_close_prices(data2["result"])


def _calculate_spread(series_1, series_2, hedge_ratio):
    return pd.DataFrame(series_1) - (pd.DataFrame(series_2) * hedge_ratio)


@dataclass
class Cointegration:
    _p_value: float
    _c_value: float
    _t_value: float
    cointegrated: bool
    zero_crossings: int

    @property
    def p_value(self):
        return round(self._p_value, 2)

    @property
    def c_value(self):
        return round(self._c_value, 2)

    @property
    def t_value(self):
        return round(self._t_value, 2)


def calculate_cointegration(series_1, series_2):
    coint_flag = False
    coint_result = coint(series_1, series_2)

    t_value = coint_result[0]
    p_value = coint_result[1]
    c_value = coint_result[2][1] # critical value

    # OLS is one (of many) function for calculating hedge ratio
    model = sm.OLS(series_1, series_2).fit()
    hedge_ratio = model.params[0]

    spread = _calculate_spread(series_1, series_2, hedge_ratio)

    # np.where(<condition>) --> returns elements which are non-zero
    # np.diff(<array>) --> returns difference between two contiguous elements
    # np.sign(<array>) --> returns -1 for negative numbers, 0 for 0, and 1 for positive numbers
    zero_crossings = len(np.where(np.diff(np.sign(spread)))[0])

    if p_value < 0.5 and t_value < c_value:
        coint_flag = True

    return Cointegration(
        p_value,
        c_value,
        t_value,
        coint_flag,
        zero_crossings
    )
