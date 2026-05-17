from django.urls import path

from .views import (
    DisputePaymentView,
    EconfirmCallbackView,
    ConfirmEscrowFundedView,
    InitiatePaymentView,
    MockConfirmPaymentView,
    MyEarningsView,
    MySpendingView,
    PaymentStatusView,
    PaymentsHealthView,
    PlatformBillingSummaryView,
    PesapalIPNCallbackView,
    ReleasePaymentView,
)

urlpatterns = [
    path("", PaymentsHealthView.as_view(), name="payments-health"),
    path("initiate/<int:task_id>/", InitiatePaymentView.as_view(), name="initiate-payment"),
    path("ipn-callback/", PesapalIPNCallbackView.as_view(), name="pesapal-ipn-callback"),
    path("econfirm-callback/", EconfirmCallbackView.as_view(), name="econfirm-callback"),
    path("status/<int:task_id>/", PaymentStatusView.as_view(), name="payment-status"),
    path("confirm-funded/<int:task_id>/", ConfirmEscrowFundedView.as_view(), name="confirm-escrow-funded"),
    path("release/<int:task_id>/", ReleasePaymentView.as_view(), name="release-payment"),
    path("dispute/<int:task_id>/", DisputePaymentView.as_view(), name="dispute-payment"),
    path("my-earnings/", MyEarningsView.as_view(), name="my-earnings"),
    path("my-spending/", MySpendingView.as_view(), name="my-spending"),
    path("platform-billing/", PlatformBillingSummaryView.as_view(), name="platform-billing"),
    path(
        "mock-confirm/<int:transaction_id>/",
        MockConfirmPaymentView.as_view(),
        name="mock-confirm-payment",
    ),
]
