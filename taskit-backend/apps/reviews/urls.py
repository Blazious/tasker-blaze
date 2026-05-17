from django.urls import path

from .views import ReportUserView, ReviewsHealthView, SubmitReviewView, UserReviewsView

urlpatterns = [
    path("", ReviewsHealthView.as_view(), name="reviews-health"),
    path("submit/<int:task_id>/", SubmitReviewView.as_view(), name="submit-review"),
    path("report-user/<int:user_id>/", ReportUserView.as_view(), name="report-user"),
    path("user/<int:user_id>/", UserReviewsView.as_view(), name="user-reviews"),
]
