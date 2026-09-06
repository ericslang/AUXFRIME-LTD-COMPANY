#!/usr/bin/env bash
set -o errexit

python manage.py collectstatic --no-input
python manage.py migrate

if [ "${IMPORT_FIXTURE_ON_START:-false}" = "true" ]; then
  if [ -f "render-fixture.json" ]; then
    existing_users="$(python manage.py shell -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.count())")"
    if [ "${FORCE_FIXTURE_IMPORT:-false}" != "true" ] && [ "${existing_users}" -gt 0 ]; then
      echo "Skipping fixture import: ${existing_users} user(s) already exist. Set FORCE_FIXTURE_IMPORT=true to override."
    else
      echo "IMPORT_FIXTURE_ON_START=true; loading render-fixture.json"
      if python manage.py loaddata render-fixture.json; then
        echo "Fixture import completed successfully."
      else
        if [ "${IMPORT_FIXTURE_FAIL_HARD:-false}" = "true" ]; then
          echo "Fixture import failed and IMPORT_FIXTURE_FAIL_HARD=true, exiting."
          exit 1
        fi
        echo "Fixture import failed, continuing startup. Set IMPORT_FIXTURE_FAIL_HARD=true to fail startup on import errors."
      fi
    fi
  else
    echo "IMPORT_FIXTURE_ON_START=true but render-fixture.json not found"
  fi
fi

gunicorn tracker.wsgi:application --log-file -