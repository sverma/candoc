#!/usr/bin/env bash
set -euo pipefail
umask 077
cd /opt/candock
backup_dir=/var/backups/candock
mkdir -p "$backup_dir"
exec 9>"$backup_dir/.lock"
flock -n 9 || exit 0
stamp=$(date -u +%Y%m%dT%H%M%SZ)
destination="$backup_dir/$stamp"
mkdir "$destination"
trap 'rm -rf "$destination"' ERR
docker compose exec -T db pg_dump -U candock -d candock --no-owner --no-acl | gzip > "$destination/database.sql.gz"
# Database is the authoritative text/assessment record. Original documents are
# private supplemental files, backed up independently of source releases.
docker compose exec -T api tar -C /data -czf - resumes > "$destination/resumes.tar.gz"
gzip -t "$destination/database.sql.gz"
tar -tzf "$destination/resumes.tar.gz" >/dev/null
find "$backup_dir" -mindepth 1 -maxdepth 1 -type d -mtime +6 -exec rm -rf {} +
printf 'Candoc backup completed: %s\n' "$stamp"
