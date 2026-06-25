from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


REDACT_KEYS = {"raw_html"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    """Return diagnostics for a config entry.

    No passwords or cookies are returned. Parsed account information and short
    parser contexts are included so portal layout changes can be diagnosed.
    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}

    # Remove raw HTML and other potentially sensitive values
    sanitized = {k: v for k, v in data.items() if k not in REDACT_KEYS}

    return {"apa_arad": sanitized}
