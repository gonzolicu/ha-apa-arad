from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ApaAradCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> Any:
        try:
            return await self.api.async_fetch_parsed_dashboard()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Compania de Apa Arad: {err}") from err
