web: gunicorn minds.wsgi:application --workers 3 --bind 0.0.0.0:$PORT
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
