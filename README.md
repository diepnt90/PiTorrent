# PiTorrent

PiTorrent is a lightweight self-hosted torrent download manager for Raspberry Pi, built around Transmission and Docker. Downloads are stored on external storage, while a simple web dashboard provides torrent management, per-file selection, completed-file management, subtitle attachment, browser playback, and FTP access for completed files.

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
- Read-only anonymous FTP access for completed files
- No Stremio/Nuvio addon
- No SMB service

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

LAN devices / VLC
   |
   | ftp://PI-IP/
   v
 FTP (anonymous, read-only)
   |
   +--> /mnt/pitorrent/downloads/complete

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

## FTP access

Completed files are shared over anonymous FTP:

```text
ftp://<PI-IP>/
```

Example:

```text
ftp://192.168.1.50/
```

The FTP service is:

- anonymous login
- no password required
- read-only
- TCP port `21`
- passive ports `21100-21110`

### VLC / Android TV

In VLC, open the network/local-network section and add or open:

```text
ftp://<PI-IP>/
```

If VLC asks for credentials:

```text
Username: anonymous
Password: leave blank
```

### Desktop test

You can test the FTP service from another machine with:

```bash
curl ftp://<PI-IP>/
```

## Downloading a torrent

1. Paste a magnet link or `.torrent` URL into the PiTorrent dashboard.
2. PiTorrent retrieves torrent metadata.
3. Select the files you want.
4. Start the download.
5. Completed files appear in the dashboard and via FTP.

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

FTP logs:

```bash
docker compose logs -f ftp
```

API logs:

```bash
docker compose logs -f api
```

Transmission logs:

```bash
docker compose logs -f transmission
```

Check FTP port:

```bash
ss -lnt | grep ':21'
```

## Ports

| Port | Protocol | Purpose |
|---|---|---|
| `8080` | TCP | PiTorrent dashboard and browser media access |
| `21` | TCP | FTP control connection |
| `21100-21110` | TCP | FTP passive data connections |
| `51413` | TCP/UDP | Transmission peer traffic |

Transmission RPC (`9091`) and the internal API (`7000`) are only exposed inside Docker.

## Data persistence

Removing or rebuilding containers does not remove persistent PiTorrent data under `/mnt/pitorrent`.

## Security

The FTP service is intended only for a trusted LAN. Anonymous users can read completed files without a password, but cannot upload, modify, or delete files. Do not expose ports `21`, `21100-21110`, or `8080` directly to the public Internet.
