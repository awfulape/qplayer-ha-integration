"""Config flow for QPlayer."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import QPlayerAuthError, QPlayerClient, QPlayerError
from .const import DEFAULT_PORT, DOMAIN


class QPlayerConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            client = QPlayerClient(
                async_get_clientsession(self.hass),
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_TOKEN],
            )
            try:
                await client.state()
            except QPlayerAuthError:
                errors["base"] = "invalid_auth"
            except QPlayerError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"QPlayer ({user_input[CONF_HOST]})", data=user_input
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_TOKEN): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
