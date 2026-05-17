from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.tasks.models import Bid

from .models import Transaction


@receiver(post_save, sender=Bid)
def create_transaction_for_accepted_bid(sender, instance, **kwargs):
    if instance.status != Bid.Status.ACCEPTED:
        return

    Transaction.objects.get_or_create(
        task=instance.task,
        defaults={
            "client": instance.task.client,
            "tasker": instance.tasker,
            "agreed_amount": instance.amount,
        },
    )
