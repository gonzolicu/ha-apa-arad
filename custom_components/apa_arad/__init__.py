from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ApaAradApi
from .coordinator import ApaAradCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    api = ApaAradApi(username, password, async_get_clientsession(hass))

    # Verify credentials
    success = await api.async_login()
    if not success:
        await api.async_close()
        raise ConfigEntryAuthFailed("Failed to authenticate with Compania de Apa Arad")

    coordinator = ApaAradCoordinator(hass, api)
    # Perform first refresh so entities have data
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    # Close underlying session
    try:
        await coordinator.api.async_close()
    except Exception:  # pragma: no cover - best effort cleanup
        _LOGGER.exception("Error closing API session")

    return unload_ok
