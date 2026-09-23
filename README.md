# PiTorrent

PiTorrent is a lightweight self-hosted torrent download manager for Raspberry Pi, built around Transmission and Docker. Downloads are stored on external storage, while a simple web dashboard provides torrent management, per-file selection, completed-file management, subtitle attachment, and browser playback.

## Features

- Lightweight web dashboard on port `8080`
- Add torrents using magnet links or `.torrent` URLs
- Fetch magnet metadata before downloading
- Select individual files from multi-file torrents
- Pause, resume, remove, or remove torrent + files
- Download/upload speed, peer count, progress, and USB free-space display
- Completed-file list and browser playback
- `Add sub` button for each completed video
- Attach subtitles by direct URL or local upload
- Persistent subtitle mappings
- No Stremio/Nuvio addon
- No SMB or FTP service

## Architecture

```text
Browser
   |
   | http://PI-IP:8080
   v
 nginx / PiTorrent Web UI
   |          |
   |          +--> Internal API
   |          |      |- subtitle management
   |          |      |- browser subtitle conversion
   |          |      `- redirect checker
   |          |
   |          +--> Transmission RPC
   |
   +--> completed media from USB

External storage
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

## Downloading a torrent

1. Paste a magnet link or `.torrent` URL into the PiTorrent dashboard.
2. PiTorrent retrieves torrent metadata.
3. Select the files you want.
4. Start the download.
5. Completed files appear in the dashboard.

## Adding subtitles

Each completed video has an **Add sub** button.

Supported uploaded subtitle formats:

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

Mappings are stored in:

```text
/mnt/pitorrent/data/subtitles/mappings.json
```

## Updating PiTorrent

```bash
cd ~/PiTorrent
git pull
docker compose down
docker compose up -d --build
```

## Useful commands

Check containers:

```bash
docker compose ps
```

API logs:

```bash
docker compose logs -f api
```

Transmission logs:

```bash
docker compose logs -f transmission
```

Web logs:

```bash
docker compose logs -f web
```

## Ports

| Port | Protocol | Purpose |
|---|---|---|
| `8080` | TCP | PiTorrent dashboard and browser media access |
| `51413` | TCP/UDP | Transmission peer traffic |

Transmission RPC (`9091`) and the internal API (`7000`) are only exposed inside Docker.

## Data persistence

Removing or rebuilding containers does not remove persistent PiTorrent data under `/mnt/pitorrent`.

## Security

The default configuration is intended for a trusted LAN. Do not expose port `8080` directly to the public Internet without authentication and HTTPS.
