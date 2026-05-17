from .utils import get_average_rating, get_completed_tasks_count


def get_badges(user):
    completed_tasks_count = get_completed_tasks_count(user)
    average_rating = get_average_rating(user)
    badges = []

    if completed_tasks_count >= 1:
        badges.append("First Task")
    if completed_tasks_count >= 5 and average_rating >= 4.0:
        badges.append("Rising Star")
    if completed_tasks_count >= 10 and average_rating >= 4.5:
        badges.append("Top Rated")
    if completed_tasks_count >= 20:
        badges.append("Trusted Tasker")

    return badges
