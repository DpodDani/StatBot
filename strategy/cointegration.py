import math


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