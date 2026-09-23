#!/bin/sh
set -e

SRC=/source
DST=/ftp-root

rm -rf "$DST"
mkdir -p "$DST"

# Flatten every file under completed downloads into the FTP root.
# No media data is copied: symlinks point back to the read-only source.
find "$SRC" -type f | while IFS= read -r src; do
  base="$(basename "$src")"
  name="$base"
  stem="${base%.*}"
  ext=""
  if [ "$stem" != "$base" ]; then
    ext=".${base##*.}"
  else
    stem="$base"
  fi

  n=2
  while [ -e "$DST/$name" ] || [ -L "$DST/$name" ]; do
    name="${stem} (${n})${ext}"
    n=$((n+1))
  done

  ln -s "$src" "$DST/$name"
done

exec vsftpd /etc/vsftpd/vsftpd.conf
