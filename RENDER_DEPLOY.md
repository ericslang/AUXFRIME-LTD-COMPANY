Render deployment and persistent login data

1) Keep a persistent database on Render
- Use the managed PostgreSQL database defined in render.yaml.
- Do not delete the Render database service if you want to keep users and app data.
- Your web service can be redeployed safely; data stays in PostgreSQL.

Build/runtime note:
- render.yaml now uses a build command that only installs dependencies.
- Django commands (collectstatic, migrate) run in startCommand where DATABASE_URL is available.

2) Required environment variables on Render
- DEBUG=False
- DJANGO_SECRET_KEY=<long random value>
- DATABASE_URL=<from the Render PostgreSQL service>
- ALLOWED_HOSTS=<your Render host and any custom domain>
- CSRF_TRUSTED_ORIGINS=<https://your Render host and custom domain>

Notes:
- tracker/settings.py already reads RENDER_EXTERNAL_HOSTNAME and appends it to ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS.
- In production mode, startup fails intentionally if DATABASE_URL is missing.

3) One-time migration of login credentials (SQLite -> Render PostgreSQL)
Run this locally from the project root:

  .\venv\Scripts\python.exe manage.py dumpdata auth.user --natural-primary --indent 2 --output render-users.json

Commit and push render-users.json temporarily.

If Render Shell is unavailable on your plan, use env-driven startup import:
- Set IMPORT_FIXTURE_ON_START=true in Render environment.
- Deploy once. The app startup will run migrate and then loaddata automatically.
- Set IMPORT_FIXTURE_ON_START=false after successful login verification.
- Default fixture filename is render-users.json.
- You can override with IMPORT_FIXTURE_FILE=<filename>.
- If users already exist, import is skipped by default to avoid conflicts.
- Set FORCE_FIXTURE_IMPORT=true only when you intentionally want to re-import.
- Set IMPORT_FIXTURE_FAIL_HARD=true if you want deploy to fail whenever import fails.

If your Render dashboard still uses build.sh directly, use build-time import instead:
- Set IMPORT_FIXTURE_ON_BUILD=true in Render environment.
- Deploy once and check build logs for "loading render-users.json".
- Set IMPORT_FIXTURE_ON_BUILD=false after successful login verification.

If Render Shell is available, you can still run:
  python manage.py migrate
  python manage.py loaddata render-users.json

After successful import, remove render-fixture.json from the repo and deploy again.

4) Admin access after import
- If your local admin user existed, its password hash is imported and you can log in with the same credentials.
- If needed, create/update an admin in Render shell:

  python manage.py ensure_default_admin --username <name> --email <email> --password <password>

5) Backups
- Keep regular PostgreSQL backups (pg_dump or Render backup features if available on your plan).
- Store backups outside Render as an extra safety layer.
