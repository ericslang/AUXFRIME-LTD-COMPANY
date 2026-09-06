#!/usr/bin/env bash
set -o errexit

# Render may run build before DATABASE_URL is attached.
# Skip DB-dependent Django commands in that case.
if [ -z "${DATABASE_URL:-}" ]; then
	echo "DATABASE_URL is not set during build; skipping collectstatic/migrate."
	exit 0
fi

python manage.py collectstatic --no-input
python manage.py migrate