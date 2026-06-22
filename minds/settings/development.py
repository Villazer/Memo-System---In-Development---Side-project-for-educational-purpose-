from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # XFrameOptionsMiddleware intentionally omitted in development so the app
    # can be embedded in the v0 / Vercel preview iframe.
]

# Allow the app to be embedded in the preview iframe (CSRF needs trusted origins).
CSRF_TRUSTED_ORIGINS = [
    "https://*.vercel.app",
    "https://*.v0.app",
    "https://*.v0.dev",
    "https://*.vusercontent.net",
]
