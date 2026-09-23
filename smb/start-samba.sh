#!/bin/sh
set -e

# nmbd advertises the PiTorrent NetBIOS name/share on the LAN so clients
# such as VLC on Android TV can discover it without typing an address.
nmbd --foreground --no-process-group --debug-stdout &
NMBD_PID=$!

cleanup() {
  kill "$NMBD_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Keep the container attached to smbd.
exec smbd --foreground --no-process-group --debug-stdout
