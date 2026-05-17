from decouple import config

from .base import *

DEBUG = False

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="",
    cast=lambda value: [host.strip() for host in value.split(",") if host.strip()],
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="taskit"),
        "USER": config("POSTGRES_USER", default="taskit"),
        "PASSWORD": config("POSTGRES_PASSWORD", default=""),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="",
    cast=lambda value: [origin.strip() for origin in value.split(",") if origin.strip()],
)
