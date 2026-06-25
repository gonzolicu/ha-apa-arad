from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN

class ApaAradCoordinator(DataUpdateCoordinator):
    def __init__(self,hass,api):
        super().__init__(hass,logger=None,name=DOMAIN,update_interval=timedelta(minutes=30))
        self.api=api
    async def _async_update_data(self):
        return await self.api.async_fetch_dashboard()
