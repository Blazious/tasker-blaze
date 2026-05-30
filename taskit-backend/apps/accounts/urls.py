from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AccountsHealthView,
    ActivateTaskerView,
    AdminKYCVerificationDetailView,
    AdminKYCVerificationListView,
    AvailabilityView,
    AvailableTaskersView,
    KYCPrefillProfileView,
    KYCVerificationView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    UserStatsView,
    VerifyEmailView,
)

urlpatterns = [
    path("", AccountsHealthView.as_view(), name="accounts-health"),
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("stats/", UserStatsView.as_view(), name="user-stats"),
    path("activate-tasker/", ActivateTaskerView.as_view(), name="activate-tasker"),
    path("availability/", AvailabilityView.as_view(), name="availability"),
    path("available-taskers/", AvailableTaskersView.as_view(), name="available-taskers"),
    path("kyc/", KYCVerificationView.as_view(), name="kyc-verification"),
    path("kyc/prefill-profile/", KYCPrefillProfileView.as_view(), name="kyc-prefill-profile"),
    path("admin/kyc/", AdminKYCVerificationListView.as_view(), name="admin-kyc-list"),
    path("admin/kyc/<int:pk>/", AdminKYCVerificationDetailView.as_view(), name="admin-kyc-detail"),
]
