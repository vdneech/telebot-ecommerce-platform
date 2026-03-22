import os
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Configuration

@receiver(pre_save, sender=Configuration)
def config_delete_old_file_on_change(sender, instance, **kwargs):
    """Удаляет старый файл при обновлении картинки"""
    if not instance.pk:
        return

    try:
        old_instance = Configuration.objects.get(pk=instance.pk)
    except Configuration.DoesNotExist:
        return

    if old_instance.invoice_image and instance.invoice_image != old_instance.invoice_image:
        if os.path.isfile(old_instance.invoice_image.path):
            os.remove(old_instance.invoice_image.path)

@receiver(post_delete, sender=Configuration)
def config_delete_file_on_delete(sender, instance, **kwargs):
    """Удаляет файл при удалении записи (если модель будет удалена)"""
    if instance.invoice_image:
        if os.path.isfile(instance.invoice_image.path):
            os.remove(instance.invoice_image.path)