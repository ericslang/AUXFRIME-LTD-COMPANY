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
	fixture_file="${IMPORT_FIXTURE_FILE:-render-users.json}"
	if [ -f "${fixture_file}" ]; then
		existing_users="$(python manage.py shell -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.count())")"
		if [ "${FORCE_FIXTURE_IMPORT:-false}" != "true" ] && [ "${existing_users}" -gt 0 ]; then
			echo "Skipping fixture import during build: ${existing_users} user(s) already exist."
		else
			echo "IMPORT_FIXTURE_ON_BUILD=true; loading ${fixture_file}"
			if python manage.py loaddata "${fixture_file}"; then
				echo "Build fixture import completed successfully."
			else
				if [ "${IMPORT_FIXTURE_FAIL_HARD:-false}" = "true" ]; then
					echo "Build fixture import failed and IMPORT_FIXTURE_FAIL_HARD=true, exiting."
					exit 1
				fi
				echo "Build fixture import failed, continuing. Set IMPORT_FIXTURE_FAIL_HARD=true to fail build on import errors."
			fi
		fi
	else
		echo "IMPORT_FIXTURE_ON_BUILD=true but ${fixture_file} was not found"
	fi
fi