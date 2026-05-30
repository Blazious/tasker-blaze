from django.db.models import Avg

from apps.tasks.models import Task

from .models import Review


def get_average_rating(user):
    value = (
        Review.objects.filter(reviewee=user, is_visible=True).aggregate(
            average=Avg("rating")
        )["average"]
        or 0
    )
    return round(float(value), 2)


def get_rating_breakdown(user):
    values = Review.objects.filter(reviewee=user, is_visible=True).aggregate(
        communication=Avg("communication_rating"),
        punctuality=Avg("punctuality_rating"),
        quality=Avg("quality_rating"),
    )
    return {
        "communication": round(float(values["communication"] or 0), 2),
        "punctuality": round(float(values["punctuality"] or 0), 2),
        "quality": round(float(values["quality"] or 0), 2),
    }


def get_total_reviews(user):
    return Review.objects.filter(reviewee=user, is_visible=True).count()


def get_completed_tasks_count(user):
    return Task.objects.filter(
        assigned_tasker=user,
        status=Task.Status.COMPLETED,
    ).count()


def reveal_reviews_if_pair_complete(task):
    reviews = Review.objects.filter(task=task)
    if reviews.count() >= 2:
        for review in reviews:
            if not review.is_visible:
                review.is_visible = True
                review.save(update_fields=["is_visible"])
        return True
    return False
