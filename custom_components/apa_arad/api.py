import aiohttp

class ApaAradApi:
    def __init__(self,username,password):
        self.username=username
        self.password=password
        self.session=aiohttp.ClientSession()

    async def login(self):
        # TODO: implement using HAR analysis
        return True

    async def async_fetch_dashboard(self):
        await self.login()
        return {}
