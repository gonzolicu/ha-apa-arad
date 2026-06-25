import aiohttp


class ApaAradApi:
    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._session = aiohttp.ClientSession()

    async def async_login(self):
        # TODO: implement with real portal flow
        return True

    async def async_get_dashboard(self):
        await self.async_login()
        return {"status": "ok"}
