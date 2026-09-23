# PiTorrent

PiTorrent is a lightweight self-hosted torrent download manager for Raspberry Pi, built around Transmission and Docker. Downloads are stored on external storage, while a simple web dashboard provides torrent management, per-file selection, completed-file management, subtitle attachment, browser playback, and SMB access for completed files.

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
- Read-only SMB2/SMB3 share for completed files
- No Stremio/Nuvio addon

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

LAN devices
   |
   | smb://PI-IP/PiTorrent
   v
 Samba (read-only)
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

Check your user ID with:

```bash
id
```

If it is not UID/GID 1000, update `PUID` and `PGID` in `docker-compose.yml`.

## Storage

PiTorrent expects the external drive at:

```text
/mnt/pitorrent
```

Verify that it is mounted before starting Docker:

```bash
mountpoint /mnt/pitorrent
findmnt /mnt/pitorrent
```

Recommended persistent mount example for ext4:

```text
UUID=<YOUR-USB-UUID> /mnt/pitorrent ext4 defaults,nofail,x-systemd.device-timeout=10 0 2
```

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

## SMB access

Completed files are shared over SMB as:

```text
smb://<PI-IP>/PiTorrent
```

Examples:

```text
smb://192.168.1.50/PiTorrent
\\192.168.1.50\PiTorrent
```

The default SMB share is:

- guest access enabled
- read-only
- SMB2 minimum
- SMB3 maximum
- TCP port `445`

This is intended for a trusted home LAN. Devices can browse and play completed files but cannot modify or delete them over SMB.

### Android / Android TV

In a file manager or media player that supports SMB:

1. Add a new SMB/network location.
2. Host: Raspberry Pi IP, for example `192.168.1.50`.
3. Share name: `PiTorrent`.
4. Use guest/anonymous access.

### Windows

Open File Explorer and enter:

```text
\\<PI-IP>\PiTorrent
```

### Linux

For desktop file managers:

```text
smb://<PI-IP>/PiTorrent
```

## Downloading a torrent

1. Paste a magnet link or `.torrent` URL into the PiTorrent dashboard.
2. PiTorrent starts the torrent temporarily so Transmission can retrieve magnet metadata.
3. When metadata is ready, the torrent is stopped and the file picker is displayed.
4. Select the files you want to download.
5. Click **Start download**.
6. Completed selected files appear under **Completed files** and in the SMB share.

## Adding subtitles

Each completed video has an **Add sub** button.

A subtitle can be attached using a direct HTTP/HTTPS subtitle URL or by uploading:

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
docker compose up -d --build
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

SMB logs:

```bash
docker compose logs -f smb
```

API logs:

```bash
docker compose logs -f api
```

Transmission logs:

```bash
docker compose logs -f transmission
```

Check the internal API:

```bash
curl http://127.0.0.1:8080/api-health
```

Check SMB port:

```bash
ss -lnt | grep ':445'
```

## Ports

| Port | Protocol | Purpose |
|---|---|---|
| `8080` | TCP | PiTorrent dashboard and browser media access |
| `445` | TCP | SMB2/SMB3 read-only completed-file share |
| `51413` | TCP/UDP | Transmission peer traffic |

Transmission RPC (`9091`) and the internal API (`7000`) are only exposed inside Docker.

## Data persistence

Removing or rebuilding containers does not remove persistent PiTorrent data under `/mnt/pitorrent`.

Important paths:

```text
/mnt/pitorrent/downloads/complete
/mnt/pitorrent/downloads/incomplete
/mnt/pitorrent/data/transmission
/mnt/pitorrent/data/watch
/mnt/pitorrent/data/subtitles
```

## Security

The default configuration is intended for a trusted LAN. The SMB share allows anonymous read-only access to completed files. Do not expose ports `445` or `8080` directly to the public Internet.
