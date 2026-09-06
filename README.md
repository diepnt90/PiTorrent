# PiTorrent

PiTorrent is a lightweight self-hosted torrent download manager for Raspberry Pi, built around Transmission and Docker. Downloads are stored on an external USB drive, while a simple web dashboard provides torrent management, per-file selection, completed-file management, and subtitle attachment.

PiTorrent also includes a local Stremio/Nuvio-compatible addon that exposes completed video files on the LAN and can provide subtitles attached to each downloaded file.

## Features

- Lightweight web dashboard on port `8080`
- Add torrents using magnet links or `.torrent` URLs
- Fetch magnet metadata before downloading
- Select individual files from multi-file torrents
- Pause, resume, remove, or remove torrent + files
- Download/upload speed, peer count, progress, and USB free-space display
- Completed-file list
- External USB storage for downloads and persistent data
- Transmission resume state survives container/Pi restarts
- Local Stremio/Nuvio stream-provider addon
- Automatic matching of completed movies/episodes to Stremio/Nuvio requests
- `Add sub` button for each completed video
- Attach subtitles using a direct URL or upload a local subtitle file
- Multiple subtitle languages/files can be attached to one video
- Supported uploaded subtitle formats: `.srt`, `.vtt`, `.ass`, `.ssa`
- Subtitle mappings are persistent and do not require a media database

## Architecture

```text
Browser
   |
   | http://PI-IP:8080
   v
 nginx / PiTorrent Web UI
   |          |             |
   |          |             +--> PiTorrent addon (Flask)
   |          |                    |- Stremio/Nuvio streams
   |          |                    |- subtitles
   |          |                    `- subtitle management API
   |          |
   |          +--> Transmission RPC
   |
   +--> completed media from USB

External USB
/mnt/pitorrent/
|- downloads/
|  |- complete/
|  `- incomplete/
`- data/
   |- transmission/
   |- watch/
   `- subtitles/
      |- mappings.json
      `- files/
```

## Requirements

- Raspberry Pi or another Linux host
- Docker and Docker Compose
- External storage mounted at `/mnt/pitorrent`
- UID/GID `1000:1000` by default

Check your user ID with:

```bash
id
```

If it is not UID/GID 1000, update `PUID` and `PGID` in `docker-compose.yml`.

## USB storage

PiTorrent expects the external drive at:

```text
/mnt/pitorrent
```

Verify that it is really mounted before starting Docker:

```bash
mountpoint /mnt/pitorrent
findmnt /mnt/pitorrent
```

Recommended persistent mount example for an ext4 drive in `/etc/fstab`:

```text
UUID=<YOUR-USB-UUID> /mnt/pitorrent ext4 defaults,nofail,x-systemd.device-timeout=10 0 2
```

Using `nofail` prevents a missing USB drive from blocking the Raspberry Pi boot process.

## Installation

```bash
cd ~
git clone https://github.com/diepnt90/PiTorrent.git
cd PiTorrent

mkdir -p /mnt/pitorrent/downloads/complete
mkdir -p /mnt/pitorrent/downloads/incomplete
mkdir -p /mnt/pitorrent/data/transmission
mkdir -p /mnt/pitorrent/data/watch
mkdir -p /mnt/pitorrent/data/subtitles

sudo chown -R 1000:1000 /mnt/pitorrent/downloads
sudo chown -R 1000:1000 /mnt/pitorrent/data

docker compose up -d --build
```

Open the dashboard:

```text
http://<PI-IP>:8080/
```

For example, if the Pi is `192.168.1.50`:

```text
http://192.168.1.50:8080/
```

## Downloading a torrent

1. Paste a magnet link or `.torrent` URL into the PiTorrent dashboard.
2. PiTorrent starts the torrent temporarily so Transmission can retrieve magnet metadata.
3. When metadata is ready, the torrent is stopped and the file picker is displayed.
4. Select the files you want to download.
5. Click **Start download**.
6. Completed selected files appear under **Completed files**.

Only wanted files that have fully completed are shown in the completed-file list.

## Adding subtitles

Each completed video has an **Add sub** button.

A subtitle can be attached in two ways:

### Direct subtitle URL

Choose a language and paste a direct HTTP/HTTPS subtitle URL, for example:

```text
https://example.com/movie.en.srt
```

PiTorrent stores the URL in its subtitle mapping. The subtitle itself remains hosted by the external provider.

### Upload a subtitle

You can instead upload a subtitle file from your computer. Supported formats are:

```text
.srt
.vtt
.ass
.ssa
```

Uploaded subtitle files are stored under:

```text
/mnt/pitorrent/data/subtitles/files/
```

The video-to-subtitle mapping is stored in:

```text
/mnt/pitorrent/data/subtitles/mappings.json
```

The mapping is based on the completed video's relative path. You do not need to manually enter an IMDb ID, season, or episode number when adding a subtitle.

## Stremio / Nuvio addon

PiTorrent exposes a local stream-provider addon at:

```text
http://<PI-IP>:8080/manifest.json
```

Example:

```text
http://192.168.1.50:8080/manifest.json
```

The addon currently supports:

- `movie`
- `series`
- IMDb-style IDs (`tt...`)
- completed local video streams
- subtitles attached through the PiTorrent dashboard

The addon does not maintain a separate media library database. When Stremio/Nuvio requests a movie or episode, PiTorrent scans completed video files and chooses the best matching local file using Cinemeta metadata, titles, episode titles, and season/episode information.

The same matching process is used for subtitles. Once the requested media is matched to a local video, PiTorrent returns the subtitles attached to that video.

### Addon endpoints

```text
GET /manifest.json
GET /stream/<type>/<id>.json
GET /subtitles/<type>/<id>.json
```

For example:

```text
/stream/series/tt0086661:7:6.json
/subtitles/series/tt0086661:7:6.json
```

Uploaded subtitle files are served through `/subtitle-files/`.

## Updating PiTorrent

Because the addon is built locally, use `--build` when updating:

```bash
cd ~/PiTorrent
git pull
docker compose up -d --build
```

If nginx configuration was changed, recreating the stack with the command above is normally sufficient. To explicitly restart the web proxy:

```bash
docker compose restart web
```

## Useful commands

Check containers:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Addon logs only:

```bash
docker compose logs -f addon
```

Transmission logs only:

```bash
docker compose logs -f transmission
```

Check the addon:

```bash
curl http://127.0.0.1:8080/manifest.json
curl http://127.0.0.1:8080/addon-health
```

Check USB storage:

```bash
findmnt /mnt/pitorrent
df -hT /mnt/pitorrent
```

## Ports

| Port | Protocol | Purpose |
|---|---|---|
| `8080` | TCP | PiTorrent dashboard, addon API, media and subtitle access |
| `51413` | TCP/UDP | Transmission peer traffic |

Transmission RPC (`9091`) and the addon service (`7000`) are internal Docker services and are not exposed directly on the host. nginx provides the public routes required by the dashboard and addon.

## Data persistence

Removing or rebuilding the Docker containers does not remove the persistent PiTorrent data stored under `/mnt/pitorrent`.

Important paths:

```text
/mnt/pitorrent/downloads/complete
/mnt/pitorrent/downloads/incomplete
/mnt/pitorrent/data/transmission
/mnt/pitorrent/data/watch
/mnt/pitorrent/data/subtitles
```

Do not delete `/mnt/pitorrent/data/transmission` if you want Transmission configuration and resume information to survive container recreation.

## LAN usage

The PiTorrent addon is designed primarily for devices on the same local network as the Raspberry Pi. A URL such as:

```text
http://192.168.1.50:8080/manifest.json
```

will only work for a Nuvio/Stremio client that can reach that Raspberry Pi address.

## Security

The default configuration is intended for a trusted home LAN. Do not expose port `8080` directly to the public Internet without adding appropriate authentication, HTTPS, and access controls.
