#!/bin/bash
# Vercel static build step: install deps and collect static assets.
set -e

export DJANGO_SETTINGS_MODULE="minds.settings.production"

# The static-build runs in a uv/PEP 668 "externally managed" Python env, so we
# must allow pip to install into it. These installs are only used to run
# collectstatic during the build; the WSGI function installs its own deps.
python3 -m pip install --break-system-packages --upgrade pip
python3 -m pip install --break-system-packages -r requirements.txt

# Collect static files into STATIC_ROOT (staticfiles/), which Vercel serves
# via the route defined in vercel.json.
python3 manage.py collectstatic --noinput --clear
