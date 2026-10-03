import os
import secrets

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or secrets.token_urlsafe(48)
DEBUG = False
ALLOWED_HOSTS = ["backend", "localhost", "127.0.0.1"]
ROOT_URLCONF = "screening.urls"
WSGI_APPLICATION = "screening.wsgi.application"
INSTALLED_APPS = []
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware"]
DATABASES = {}
DEFAULT_CHARSET = "utf-8"
DATA_UPLOAD_MAX_MEMORY_SIZE = 1_000_000
