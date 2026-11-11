from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Report


@receiver(post_delete, sender=Report)
def remove_report_image(sender, instance, using, **kwargs):
    if instance.image:
        storage, name = instance.image.storage, instance.image.name
        transaction.on_commit(lambda: storage.delete(name), using=using)
