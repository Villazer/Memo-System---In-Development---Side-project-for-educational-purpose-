from .base import *
import os
import dj_database_url

DEBUG = False

# SECRET_KEY: prefer the env var, fall back to the base default so the app
# (and the build-time collectstatic) never crashes if it is missing.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or SECRET_KEY

# ALLOWED_HOSTS: combine any explicitly configured hosts with the Vercel domains.
_env_hosts = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
ALLOWED_HOSTS = _env_hosts + [".vercel.app", ".now.sh"]

_vercel_url = os.environ.get("VERCEL_URL")
if _vercel_url:
    ALLOWED_HOSTS.append(_vercel_url)

# CSRF trusted origins so POST requests (login, forms) work on the https domain.
CSRF_TRUSTED_ORIGINS = ["https://*.vercel.app", "https://*.now.sh"]
_csrf_extra = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS += [o.strip() for o in _csrf_extra.split(",") if o.strip()]

# Database: parse Neon's DATABASE_URL (pooled connection string).
_database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
if _database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=0,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME"),
            "USER": os.environ.get("DB_USER"),
            "PASSWORD": os.environ.get("DB_PASSWORD"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Non-manifest storage: static files are served by the Vercel static build
# output (see vercel.json), so we must not require a hashed manifest at runtime.
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# Vercel terminates TLS and forwards the original scheme in this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# Console-only logging: Vercel's serverless filesystem is read-only, so a
# FileHandler would crash the function on startup.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
