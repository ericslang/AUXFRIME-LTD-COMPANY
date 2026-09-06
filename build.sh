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

if [ "${IMPORT_FIXTURE_ON_BUILD:-false}" = "true" ]; then
	if [ -f "render-fixture.json" ]; then
		existing_users="$(python manage.py shell -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.count())")"
		if [ "${FORCE_FIXTURE_IMPORT:-false}" != "true" ] && [ "${existing_users}" -gt 0 ]; then
			echo "Skipping fixture import during build: ${existing_users} user(s) already exist."
		else
			echo "IMPORT_FIXTURE_ON_BUILD=true; loading render-fixture.json"
			python manage.py loaddata render-fixture.json
		fi
	else
		echo "IMPORT_FIXTURE_ON_BUILD=true but render-fixture.json not found"
	fi
fi