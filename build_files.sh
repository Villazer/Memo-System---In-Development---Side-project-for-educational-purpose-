#!/bin/bash
# Vercel static build step: install deps and collect static assets.
set -e

export DJANGO_SETTINGS_MODULE="minds.settings.production"

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Collect static files into STATIC_ROOT (staticfiles/), which Vercel serves
# via the route defined in vercel.json.
python3 manage.py collectstatic --noinput --clear
