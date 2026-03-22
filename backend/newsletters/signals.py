import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import NewsletterImage


@receiver(post_delete, sender=NewsletterImage)
def delete_physical_file(sender, instance, **kwargs):
    """Удаляет файл с диска, если он больше не используется в базе."""

    if not instance.image or not instance.image.name:
        return

    file_path = instance.image.name
    still_used = sender.objects.filter(image=file_path).exists()

    if not still_used:
        storage = instance.image.storage
        if storage.exists(file_path):
            storage.delete(file_path)
