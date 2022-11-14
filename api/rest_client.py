from pybit import inverse_perpetual


class RestClient:
    def __init__(self, url: str):
        self._url = url
        self._client = inverse_perpetual.HTTP(endpoint=self._url)

    def get_symbols(self) -> list:
        resp = self._client.query_symbol()
        if "ret_msg" in resp and "ret_code" in resp:
            if resp["ret_msg"] == "OK" and resp["ret_code"] == 0:
                return resp["result"]
            else:
                print(f"Error in response: {resp}")
        else:
            print("No 'ret_msg' or 'ret_code' found in response")
        return []
