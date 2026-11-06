"""QPlayer integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.helpers.config_validation as cv

from .api import QPlayerAuthError, QPlayerClient, QPlayerError
from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.MEDIA_PLAYER]

SERVICE_PLAY_SEARCH = "play_search"
PLAY_SEARCH_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_id"): cv.entity_ids,
        vol.Required("query"): cv.string,
        vol.Optional("playlist"): vol.Coerce(int),
        vol.Optional("kind"): vol.In(["music", "radio"]),
    }
)


class QPlayerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: QPlayerClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.state()
        except QPlayerAuthError as err:
            raise ConfigEntryAuthFailed from err
        except QPlayerError as err:
            raise UpdateFailed(str(err)) from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = QPlayerClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_TOKEN],
    )
    coordinator = QPlayerCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_PLAY_SEARCH):

        async def _play_search(call: ServiceCall) -> None:
            from homeassistant.helpers import entity_registry as er

            registry = er.async_get(hass)
            targets = call.data.get("entity_id")
            for config_entry in hass.config_entries.async_entries(DOMAIN):
                coord: QPlayerCoordinator | None = getattr(
                    config_entry, "runtime_data", None
                )
                if coord is None:
                    continue
                if targets:
                    ids = {
                        e.entity_id
                        for e in er.async_entries_for_config_entry(
                            registry, config_entry.entry_id
                        )
                    }
                    if not ids.intersection(targets):
                        continue
                hits = await coord.client.search(
                    call.data["query"],
                    playlist=call.data.get("playlist"),
                    kind=call.data.get("kind"),
                    limit=1,
                )
                if not hits:
                    raise HomeAssistantError(
                        f"No results for '{call.data['query']}'"
                    )
                await coord.client.command(
                    "play_item", playlist=hits[0]["playlist"], index=hits[0]["index"]
                )
                await coord.async_request_refresh()

        hass.services.async_register(
            DOMAIN, SERVICE_PLAY_SEARCH, _play_search, schema=PLAY_SEARCH_SCHEMA
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok and not hass.config_entries.async_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_PLAY_SEARCH)
    return ok
