"""Small async client for the QPlayer HTTP API."""

from __future__ import annotations

from typing import Any

import aiohttp


class QPlayerError(Exception):
    """Generic API error."""


class QPlayerAuthError(QPlayerError):
    """Invalid token."""


class QPlayerClient:
    def __init__(
        self, session: aiohttp.ClientSession, host: str, port: int, token: str
    ) -> None:
        self._session = session
        self._base = f"http://{host}:{port}"
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(
        self, method: str, path: str, params: dict[str, Any] | None = None
    ) -> aiohttp.ClientResponse:
        try:
            resp = await self._session.request(
                method,
                self._base + path,
                params=params,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=10),
            )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise QPlayerError(str(err)) from err
        if resp.status == 401:
            resp.release()
            raise QPlayerAuthError("Invalid token")
        if resp.status >= 400:
            text = await resp.text()
            resp.release()
            raise QPlayerError(f"HTTP {resp.status}: {text}")
        return resp

    async def _json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = await self._request("GET", path, params)
        try:
            return await resp.json(content_type=None)
        finally:
            resp.release()

    async def _post(self, path: str, params: dict[str, Any] | None = None) -> None:
        resp = await self._request("POST", path, params)
        resp.release()

    async def state(self) -> dict[str, Any]:
        return await self._json("/api/state")

    async def playlists(self) -> list[dict[str, Any]]:
        return await self._json("/api/playlists")

    async def search(
        self,
        q: str = "",
        playlist: int | None = None,
        kind: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"q": q, "limit": limit}
        if playlist is not None:
            params["playlist"] = playlist
        if kind:
            params["kind"] = kind
        return await self._json("/api/search", params)

    async def cover(self) -> tuple[bytes, str] | None:
        try:
            resp = await self._request("GET", "/api/cover")
        except QPlayerAuthError:
            raise
        except QPlayerError:
            return None
        try:
            return await resp.read(), resp.content_type
        finally:
            resp.release()

    async def command(self, name: str, **params: Any) -> None:
        clean = {k: _fmt(v) for k, v in params.items() if v is not None}
        await self._post(f"/api/{name}", clean)


def _fmt(value: Any) -> Any:
    if isinstance(value, bool):
        return "1" if value else "0"
    return value
