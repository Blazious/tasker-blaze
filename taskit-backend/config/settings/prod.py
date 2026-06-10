import dj_database_url
from decouple import config

from .base import *

DEBUG = False

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
if EMAIL_VERIFICATION_ENABLED and EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
    missing_email_settings = [
        name
        for name, value in {
            "EMAIL_HOST": EMAIL_HOST,
            "EMAIL_HOST_USER": EMAIL_HOST_USER,
            "EMAIL_HOST_PASSWORD": EMAIL_HOST_PASSWORD,
            "DEFAULT_FROM_EMAIL": DEFAULT_FROM_EMAIL,
        }.items()
        if not value or value == "noreply@taskit.local"
    ]
    if missing_email_settings:
        raise RuntimeError(
            "Production email verification requires SMTP settings: "
            + ", ".join(missing_email_settings)
        )


def normalize_origin(origin):
    return origin.strip().rstrip("/")


def parse_origin_list(value):
    return [normalize_origin(origin) for origin in value.split(",") if origin.strip()]


ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="",
    cast=lambda value: [host.strip() for host in value.split(",") if host.strip()],
)
for host in [
    "healthcheck.railway.app",
    ".up.railway.app",
    ".railway.app",
    config("RAILWAY_PUBLIC_DOMAIN", default=""),
]:
    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="",
    cast=parse_origin_list,
)
for origin in [
    "https://tasker-blaze.vercel.app",
    normalize_origin(config("FRONTEND_URL", default="")),
]:
    if origin and origin not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(origin)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="",
    cast=parse_origin_list,
)
for origin in [
    "https://tasker-blaze.vercel.app",
    normalize_origin(config("FRONTEND_URL", default="")),
]:
    if origin and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default="True").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
