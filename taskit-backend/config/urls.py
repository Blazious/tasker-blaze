from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.reviews.views import PublicProfileView


@api_view(["GET"])
def api_root(request):
    return Response(
        {
            "message": "Taskit backend is running.",
            "routes": {
                "admin": "/admin/",
                "auth": "/api/v1/auth/",
                "tasks": "/api/v1/tasks/",
                "payments": "/api/v1/payments/",
                "chat": "/api/v1/chat/",
                "reviews": "/api/v1/reviews/",
                "notifications": "/api/v1/notifications/",
                "support": "/api/v1/support/",
            },
        }
    )


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok", "version": "1.0.0"})

urlpatterns = [
    path("", api_root, name="api-root"),
    path("health/", health_check, name="railway-health-check"),
    path("admin/", admin.site.urls),
    path("auth/", include("apps.accounts.urls")),
    path("api/v1/health/", health_check, name="health-check"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/tasks/", include("apps.tasks.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/chat/", include("apps.chat.urls")),
    path("api/v1/reviews/", include("apps.reviews.urls")),
    path("api/v1/profiles/<int:user_id>/", PublicProfileView.as_view(), name="public-profile"),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/support/", include("apps.support.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
