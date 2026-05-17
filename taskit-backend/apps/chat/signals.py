from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.tasks.models import Bid

from .models import ChatThread


@receiver(post_save, sender=Bid)
def create_chat_thread_for_accepted_bid(sender, instance, **kwargs):
    if instance.status != Bid.Status.ACCEPTED:
        return

    thread, _ = ChatThread.objects.get_or_create(task=instance.task)
    thread.participants.add(instance.task.client, instance.tasker)
