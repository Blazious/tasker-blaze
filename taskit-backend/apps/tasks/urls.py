from django.urls import path

from .views import (
    AcceptBidView,
    BidListCreateView,
    MyAssignmentsView,
    MyBidsView,
    MyTasksView,
    RejectBidView,
    TaskCategoryListView,
    TaskDetailView,
    TaskListCreateView,
)

urlpatterns = [
    path("", TaskListCreateView.as_view(), name="task-list-create"),
    path("categories/", TaskCategoryListView.as_view(), name="task-categories"),
    path("my-tasks/", MyTasksView.as_view(), name="my-tasks"),
    path("my-assignments/", MyAssignmentsView.as_view(), name="my-assignments"),
    path("my-bids/", MyBidsView.as_view(), name="my-bids"),
    path("<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("<int:task_id>/bids/", BidListCreateView.as_view(), name="task-bids"),
    path(
        "<int:task_id>/bids/<int:bid_id>/accept/",
        AcceptBidView.as_view(),
        name="accept-bid",
    ),
    path(
        "<int:task_id>/bids/<int:bid_id>/reject/",
        RejectBidView.as_view(),
        name="reject-bid",
    ),
]
