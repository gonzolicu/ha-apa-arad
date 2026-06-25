from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ApaAradApi
from .const import DOMAIN, NAME


async def _async_validate_credentials(
    hass: HomeAssistant, username: str, password: str
) -> bool:
    """Validate credentials against the Apa Arad portal."""
    api = ApaAradApi(username, password, async_get_clientsession(hass))
    return await api.async_login()


def _validate_email_username(username: str) -> bool:
    """Return true when the portal username looks like an email address."""
    return "@" in username


def _credentials_schema(username: str | None = None) -> vol.Schema:
    """Return the credentials form schema."""
    username_field = vol.Required(CONF_USERNAME)
    if username:
        username_field = vol.Required(CONF_USERNAME, default=username)

    return vol.Schema(
        {
            username_field: selector.TextSelector(),
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
    )


class ApaAradConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            if not _validate_email_username(user_input[CONF_USERNAME]):
                errors["base"] = "email_required"
            elif not await _async_validate_credentials(
                self.hass, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            ):
                errors["base"] = "invalid_auth"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=NAME, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=_credentials_schema(), errors=errors
        )

    async def async_step_reauth(self, entry_data):
        """Handle reauth requested by Home Assistant."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Confirm credentials during reauth."""
        errors = {}
        username = self._reauth_entry.data[CONF_USERNAME]

        if user_input is not None:
            updated_data = {
                **self._reauth_entry.data,
                CONF_USERNAME: username,
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }

            if not await _async_validate_credentials(
                self.hass, username, user_input[CONF_PASSWORD]
            ):
                errors["base"] = "invalid_auth"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates=updated_data,
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={CONF_USERNAME: username},
        )

    async def async_step_import(self, user_input):
        """Handle import from YAML."""
        return await self.async_step_user(user_input)

    @callback
    def async_get_options_flow(self, config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        return self.async_create_entry(title="Options", data={})
