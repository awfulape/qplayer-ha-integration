"""QPlayer media player entity."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.components.media_player.browse_media import (
    BrowseError,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import QPlayerCoordinator
from .api import QPlayerError
from .const import DOMAIN

BROWSE_LIMIT = 100
ROOT_ID = "root"

BASE_FEATURES = (
    MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SHUFFLE_SET
    | MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.BROWSE_MEDIA
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([QPlayerMediaPlayer(entry.runtime_data, entry)])


class QPlayerMediaPlayer(CoordinatorEntity[QPlayerCoordinator], MediaPlayerEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_media_content_type = MediaType.MUSIC

    def __init__(self, coordinator: QPlayerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry.unique_id or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="QPlayer",
        )
        self._last_position: float | None = None
        self._position_updated_at = None

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data or {}

    def _handle_coordinator_update(self) -> None:
        pos = self._data.get("position")
        if pos != self._last_position or self.state == MediaPlayerState.PLAYING:
            self._position_updated_at = dt_util.utcnow()
        self._last_position = pos
        super()._handle_coordinator_update()

    @property
    def state(self) -> MediaPlayerState:
        return {
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
        }.get(self._data.get("state"), MediaPlayerState.IDLE)

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        if self._data.get("source") == "radio":
            return BASE_FEATURES
        return BASE_FEATURES | MediaPlayerEntityFeature.SEEK

    @property
    def media_title(self) -> str | None:
        return self._data.get("title") or None

    @property
    def media_artist(self) -> str | None:
        return self._data.get("artist") or None

    @property
    def media_album_name(self) -> str | None:
        return self._data.get("album") or None

    @property
    def media_playlist(self) -> str | None:
        return self._data.get("playlist") or None

    @property
    def media_duration(self) -> int | None:
        if self._data.get("source") != "music":
            return None
        d = self._data.get("duration")
        return int(d) if d else None

    @property
    def media_position(self) -> int | None:
        if self._data.get("source") != "music":
            return None
        p = self._data.get("position")
        return int(p) if p is not None else None

    @property
    def media_position_updated_at(self):
        if self.media_position is None:
            return None
        return self._position_updated_at

    @property
    def volume_level(self) -> float | None:
        v = self._data.get("volume")
        return v / 100 if v is not None else None

    @property
    def is_volume_muted(self) -> bool | None:
        return self._data.get("muted")

    @property
    def shuffle(self) -> bool | None:
        return self._data.get("shuffle")

    @property
    def media_image_hash(self) -> str | None:
        if not self._data.get("hasCover"):
            return None
        return f"{self._data.get('playlistIndex')}-{self._data.get('index')}-{self._data.get('title')}"

    @property
    def media_image_remotely_accessible(self) -> bool:
        return False

    async def async_get_media_image(self) -> tuple[bytes | None, str | None]:
        try:
            result = await self.coordinator.client.cover()
        except QPlayerError:
            return None, None
        return result if result else (None, None)

    async def _cmd(self, name: str, **params: Any) -> None:
        await self.coordinator.client.command(name, **params)
        await self.coordinator.async_request_refresh()

    async def async_media_play(self) -> None:
        await self._cmd("play")

    async def async_media_pause(self) -> None:
        await self._cmd("pause")

    async def async_media_stop(self) -> None:
        await self._cmd("stop")

    async def async_media_next_track(self) -> None:
        await self._cmd("next")

    async def async_media_previous_track(self) -> None:
        await self._cmd("previous")

    async def async_media_seek(self, position: float) -> None:
        await self._cmd("seek", position=position)

    async def async_set_volume_level(self, volume: float) -> None:
        await self._cmd("volume", level=round(volume * 100))

    async def async_mute_volume(self, mute: bool) -> None:
        await self._cmd("mute", enabled=mute)

    async def async_set_shuffle(self, shuffle: bool) -> None:
        await self._cmd("shuffle", enabled=shuffle)

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        client = self.coordinator.client
        if media_id.startswith("item:"):
            _, playlist, index = media_id.split(":")
            await self._cmd("play_item", playlist=int(playlist), index=int(index))
            return
        hits = await client.search(media_id, limit=1)
        if not hits:
            raise BrowseError(f"No results for '{media_id}'")
        await self._cmd("play_item", playlist=hits[0]["playlist"], index=hits[0]["index"])

    async def async_browse_media(
        self, media_content_type: str | None = None, media_content_id: str | None = None
    ) -> BrowseMedia:
        client = self.coordinator.client
        if not media_content_id or media_content_id == ROOT_ID:
            playlists = await client.playlists()
            return BrowseMedia(
                title="QPlayer",
                media_class="directory",
                media_content_id=ROOT_ID,
                media_content_type="library",
                can_play=False,
                can_expand=True,
                children=[
                    BrowseMedia(
                        title=f"{p['name']} ({p['count']})" if p.get("indexed") else p["name"],
                        media_class="directory",
                        media_content_id=f"playlist:{p['index']}",
                        media_content_type="playlist",
                        can_play=False,
                        can_expand=True,
                    )
                    for p in playlists
                ],
            )
        if media_content_id.startswith("playlist:"):
            idx = int(media_content_id.split(":")[1])
            items = await client.search("", playlist=idx, limit=BROWSE_LIMIT)
            return BrowseMedia(
                title=f"Playlist {idx} (first {BROWSE_LIMIT})",
                media_class="directory",
                media_content_id=media_content_id,
                media_content_type="playlist",
                can_play=False,
                can_expand=True,
                children=[
                    BrowseMedia(
                        title=(
                            f"{i['artist']} - {i['title']}" if i.get("artist") else i["title"]
                        ),
                        media_class="music",
                        media_content_id=f"item:{i['playlist']}:{i['index']}",
                        media_content_type=MediaType.MUSIC,
                        can_play=True,
                        can_expand=False,
                    )
                    for i in items
                ],
            )
        raise BrowseError(f"Unknown media id {media_content_id}")
