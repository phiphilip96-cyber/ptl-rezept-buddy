#!/bin/bash
# /opt/coaching/backup.sh — nächtlicher Dump, wird von der Synology per rsync-Pull abgeholt (wie Paperless)
set -e
ZIEL=/opt/backups/coaching
mkdir -p "$ZIEL"
docker compose -f /opt/coaching/docker-compose.yml exec -T mongo mongodump --archive --gzip > "$ZIEL/mongo-$(date +%F).archive.gz"
tar czf "$ZIEL/prompts-$(date +%F).tgz" -C /opt/coaching/ptl-rezept-buddy prompts
find "$ZIEL" -type f -mtime +14 -delete
