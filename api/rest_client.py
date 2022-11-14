from pybit import inverse_perpetual


class RestClient:
    def __init__(self, url: str):
        self._url = url
        self._client = inverse_perpetual.HTTP(endpoint=self._url)

    def get_symbols(self, trading=None, maker_rebate=False) -> list:
        symbols = []
        resp = self._client.query_symbol()

        if "ret_msg" not in resp or "ret_code" not in resp:
            print("No 'ret_msg' or 'ret_code' found in response")
            return symbols

        if resp["ret_msg"] != "OK" or resp["ret_code"] != 0:
            print(f"Error in response: {resp}")
            return symbols

        symbols = resp["result"]

        if trading:
            symbols = list(filter(lambda x: x["status"] == "Trading", symbols))

        if maker_rebate:
            symbols = list(filter(lambda x: float(x["maker_fee"]) < 0, symbols))

        return symbols
