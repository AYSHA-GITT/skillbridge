#!/bin/sh
# Nightly backup of the database and uploaded files. Keeps 14 days.
# Install on the server:  crontab -e  ->  30 2 * * * /home/ubuntu/skillbridge/deploy/backup.sh
set -eu
cd "$(dirname "$0")"
DEST="$HOME/skillbridge-backups"
STAMP="$(date +%Y-%m-%d_%H%M)"
mkdir -p "$DEST"
docker compose --env-file production.env exec -T db \
  pg_dump -U skillbridge -d skillbridge --format=custom > "$DEST/db_$STAMP.dump"
docker compose --env-file production.env exec -T api \
  tar -czf - -C /app uploads > "$DEST/uploads_$STAMP.tar.gz"
find "$DEST" -type f -mtime +14 -delete
echo "Backup written to $DEST ($STAMP)"
