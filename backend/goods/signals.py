from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from goods.models import GoodImage

@receiver(pre_save, sender=GoodImage)
def goodimage_delete_old_file_on_change(sender, instance: GoodImage, **kwargs):
    if not instance.pk:
        return

    try:
        old = GoodImage.objects.get(pk=instance.pk)
    except GoodImage.DoesNotExist:
        return

    if old.image and instance.image and old.image.name != instance.image.name:
        old.image.delete(save=False)

@receiver(post_delete, sender=GoodImage)
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