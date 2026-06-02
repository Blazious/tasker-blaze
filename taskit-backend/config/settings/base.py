from pathlib import Path

import cloudinary
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="change-me-in-production")
DEBUG = config("DEBUG", default="False").lower() in {"1", "true", "yes", "on"}

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=lambda value: [host.strip() for host in value.split(",") if host.strip()],
)

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "channels",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "cloudinary",
    "cloudinary_storage",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.tasks",
    "apps.payments",
    "apps.chat",
    "apps.reviews",
    "apps.notifications",
    "apps.support",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [config("REDIS_URL", default="redis://127.0.0.1:6379/0")],
        },
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1
AUTH_USER_MODEL = "accounts.User"
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@taskit.local")
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default="True").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
EMAIL_VERIFICATION_ENABLED = config(
    "EMAIL_VERIFICATION_ENABLED",
    default="True",
).lower() in {"1", "true", "yes", "on"}
ADMIN_EMAIL = config("ADMIN_EMAIL", default="admin@taskit.co.ke")
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173").rstrip("/")
KYC_MOCK = config("KYC_MOCK", default="True").lower() in {"1", "true", "yes", "on"}
KYC_OCR_PROVIDER = config("KYC_OCR_PROVIDER", default="mindee")
KYC_ENABLE_LOCAL_OCR = config("KYC_ENABLE_LOCAL_OCR", default="False").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
KYC_ENABLE_FACE_MATCH = config("KYC_ENABLE_FACE_MATCH", default="False").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
KYC_FACE_MATCH_THRESHOLD = config("KYC_FACE_MATCH_THRESHOLD", default="75")
KYC_HTTP_TIMEOUT = config("KYC_HTTP_TIMEOUT", default=30, cast=int)
MINDEE_API_KEY = config("MINDEE_API_KEY", default="")
MINDEE_MODEL_ID = config("MINDEE_MODEL_ID", default="")
MINDEE_ENDPOINT_URL = config("MINDEE_ENDPOINT_URL", default="")
INSIGHTFACE_MODEL_NAME = config("INSIGHTFACE_MODEL_NAME", default="buffalo_l")
INSIGHTFACE_CTX_ID = config("INSIGHTFACE_CTX_ID", default=-1, cast=int)

CLOUDINARY_CLOUD_NAME = config("CLOUDINARY_CLOUD_NAME", default="")
CLOUDINARY_API_KEY = config("CLOUDINARY_API_KEY", default="")
CLOUDINARY_API_SECRET = config("CLOUDINARY_API_SECRET", default="")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME or None,
    api_key=CLOUDINARY_API_KEY or None,
    api_secret=CLOUDINARY_API_SECRET or None,
)

PESAPAL_ENV = config("PESAPAL_ENV", default="sandbox")
PESAPAL_CONSUMER_KEY = config("PESAPAL_CONSUMER_KEY", default="")
PESAPAL_CONSUMER_SECRET = config("PESAPAL_CONSUMER_SECRET", default="")
PESAPAL_IPN_ID = config("PESAPAL_IPN_ID", default="")
PESAPAL_CALLBACK_URL = config("PESAPAL_CALLBACK_URL", default="")
PESAPAL_MOCK = config("PESAPAL_MOCK", default="False").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
PESAPAL_REGISTER_IPN_ON_STARTUP = config(
    "PESAPAL_REGISTER_IPN_ON_STARTUP",
    default="False",
).lower() in {"1", "true", "yes", "on"}
PESAPAL_IPN_URL = config("PESAPAL_IPN_URL", default="")

ECONFIRM_API_KEY = config("ECONFIRM_API_KEY", default="")
ECONFIRM_BASE_URL = config("ECONFIRM_BASE_URL", default="https://econfirm.co.ke/api/v1")
ECONFIRM_CALLBACK_URL = config("ECONFIRM_CALLBACK_URL", default="")
ECONFIRM_PLATFORM_FEE_PERCENT = config("PLATFORM_FEE_PERCENT", default=10, cast=int)
ECONFIRM_MOCK = config("ECONFIRM_MOCK", default="False").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

INTASEND_SECRET_KEY = config("INTASEND_SECRET_KEY", default="")
INTASEND_PUBLISHABLE_KEY = config("INTASEND_PUBLISHABLE_KEY", default="")
INTASEND_TEST_MODE = config("INTASEND_TEST_MODE", default="True").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
INTASEND_BASE_URL = config(
    "INTASEND_BASE_URL",
    default=(
        "https://sandbox.intasend.com/api/v1"
        if INTASEND_TEST_MODE
        else "https://payment.intasend.com/api/v1"
    ),
)
INTASEND_WEBHOOK_CHALLENGE = config("INTASEND_WEBHOOK_CHALLENGE", default="")
ENABLE_TEST_BILLING_TOOLS = config("ENABLE_TEST_BILLING_TOOLS", default="False").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

GEMINI_API_KEY = config("GEMINI_API_KEY", default="")
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-2.5-flash")
GEMINI_HTTP_TIMEOUT = config("GEMINI_HTTP_TIMEOUT", default=30, cast=int)

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
}
