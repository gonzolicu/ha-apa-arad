from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .parser import compute_amount_due

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
            data = await self.api.async_fetch_parsed_dashboard()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Compania de Apa Arad: {err}") from err
        data.update(compute_amount_due(data, dt_util.now().date()))
        return data
