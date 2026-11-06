# QPlayer – Home Assistant integration

Controls QPlayer2 over its HTTP API as a `media_player` entity.

## 1. Enable the API in the player

Edit `~/.config/qplayer/qplayer-settings-v1.json` (player closed):

```json
"api": { "enabled": true, "bind": "0.0.0.0", "port": 8765, "token": "<secret>" }
```

If `token` is empty, the player generates one on start; read it from the file. Restart the player.
The API is plain HTTP; use only on a trusted LAN.

## 2. Install

Copy `custom_components/qplayer` into HA's `config/custom_components/` and restart HA
(or add this repo to HACS as a custom repository). Then: Settings → Devices & services →
Add integration → QPlayer → host, port, token.

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
