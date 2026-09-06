# PiTorrent

Lightweight Raspberry Pi torrent dashboard based on Transmission, with downloads stored on the external USB mounted at `/mnt/pitorrent`.

## Storage layout

- `/mnt/pitorrent/downloads` — downloaded torrent data
- `/mnt/pitorrent/data/transmission` — Transmission configuration and resume state
- `/mnt/pitorrent/data/watch` — optional watch directory

## Run on Raspberry Pi

```bash
cd ~
git clone https://github.com/diepnt90/PiTorrent.git
cd PiTorrent
mkdir -p /mnt/pitorrent/downloads /mnt/pitorrent/data/transmission /mnt/pitorrent/data/watch
docker compose up -d
```

Open:

```text
http://<PI-IP>:8080
```

## Update later

```bash
cd ~/PiTorrent
git pull
docker compose pull
docker compose up -d
```

## Ports

- `8080/tcp` — PiTorrent dashboard
- `51413/tcp` and `51413/udp` — Transmission peer traffic

Transmission RPC is not exposed directly on the host; nginx proxies `/transmission/rpc` internally to Transmission.

## Notes

The USB should be mounted at `/mnt/pitorrent` before starting the stack. Check with:

```bash
mountpoint /mnt/pitorrent
findmnt /mnt/pitorrent
```

If your Linux user is not UID/GID 1000, check with `id` and update `PUID` and `PGID` in `docker-compose.yml`.
