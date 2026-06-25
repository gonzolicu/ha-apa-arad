from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import DOMAIN


REDACT_KEYS = {
    "raw_html",
    "parser_debug",
    "username",
    "service_address",
    "self_reading_code",
    "contract_number",
    "meter_number",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    """Return diagnostics for a config entry.

    No passwords or cookies are returned. Parsed account information and short
    parser contexts are included so portal layout changes can be diagnosed.
    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}

    # Remove raw HTML and other potentially sensitive values
    sanitized = async_redact_data(data, REDACT_KEYS)

    return {
        "entry": async_redact_data(
            entry.data,
            {CONF_USERNAME, CONF_PASSWORD},
        ),
        "apa_arad": sanitized,
    }
