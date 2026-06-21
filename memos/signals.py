from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import MemoRecipient


@receiver(post_save, sender=MemoRecipient)
def memo_recipient_created(sender, instance, created, **kwargs):
    pass
