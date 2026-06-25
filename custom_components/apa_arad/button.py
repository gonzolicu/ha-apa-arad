from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CREATOR, DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ApaAradRefreshButton(coordinator, entry)])


class ApaAradRefreshButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def name(self) -> str:
        return f"{self._entry.title} Actualizează"

    @property
    def unique_id(self) -> str:
        return f"apa_arad_refresh_{self._entry.entry_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=NAME,
            manufacturer=CREATOR,
            model="Compania de Apa Arad cloud account",
            configuration_url="https://myarad.croscloud.com/crosweb",
        )

    async def async_press(self) -> None:
        _LOGGER.debug("Manual refresh requested for entry %s", self._entry.entry_id)
        await self.coordinator.async_request_refresh()
