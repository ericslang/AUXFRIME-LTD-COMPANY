#!/usr/bin/env bash
set -o errexit

python manage.py collectstatic --no-input
python manage.py migrate

if [ "${IMPORT_FIXTURE_ON_START:-false}" = "true" ]; then
  if [ -f "render-fixture.json" ]; then
    echo "IMPORT_FIXTURE_ON_START=true; loading render-fixture.json"
    python manage.py loaddata render-fixture.json
  else
    echo "IMPORT_FIXTURE_ON_START=true but render-fixture.json not found"
  fi
fi

gunicorn tracker.wsgi:application --log-file -