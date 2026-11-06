# QPlayer – Home Assistant integration

Controls QPlayer2 over its HTTP API as a `media_player` entity.

## 1. Enable the API in the player

In QPlayer, open Settings (gear icon in the title bar) → API:

- Enable HTTP API
- Bind address: `0.0.0.0` (reachable from the LAN) or `127.0.0.1` (local only)
- Port: `8765`
- Token: press Generate (or enter your own); a token is required when the API is enabled

Press Save. The API is plain HTTP; use only on a trusted LAN. If Windows asks about
the firewall, allow QPlayer on private networks.

## 2. Install

### Marketplace (Home Assistant 2026.11 or newer)

HACS is built into Home Assistant as the Marketplace. Settings → Marketplace →
**Add from link** → enter this repository's GitHub URL (`owner/repository`) → Add.
Connect your GitHub account when asked (required for custom repositories). Then open
the repository page, select Install and restart Home Assistant if a repair asks for it.
Updates appear under Settings → Updates when a new release is published.

### HACS (Home Assistant 2026.10 or older)

1. HACS → ⋮ → Custom repositories → add this repository's GitHub URL, type Integration.
2. Download QPlayer from HACS and restart Home Assistant.
3. Updates appear in HACS when a new release is published.

### Manual

Copy `custom_components/qplayer` into HA's `config/custom_components/` and restart HA.

## 3. Add the integration

Settings → Devices & services → Add integration → QPlayer → host, port, token.

## Features

- Play/pause/stop/next/previous, volume, mute, shuffle, seek (not for radio), cover art
- Media browser: playlists (music and radio) → first 100 items
- `media_player.play_media` with plain text (type `music`) searches all playlists and plays the first hit
- Service `qplayer.play_search` (`query`, optional `playlist`, `kind: music|radio`) for scripts / Assist intents

Example:

```yaml
service: qplayer.play_search
data:
  query: "yle x"
  kind: radio
```
