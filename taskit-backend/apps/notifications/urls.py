from django.urls import path

from .views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationListView,
    NotificationsHealthView,
    UnreadCountView,
)

urlpatterns = [
    path("health/", NotificationsHealthView.as_view(), name="notifications-health"),
    path("", NotificationListView.as_view(), name="notification-list"),
    path("<int:pk>/read/", MarkNotificationReadView.as_view(), name="notification-read"),
    path("read-all/", MarkAllNotificationsReadView.as_view(), name="notifications-read-all"),
    path("unread-count/", UnreadCountView.as_view(), name="notifications-unread-count"),
]
