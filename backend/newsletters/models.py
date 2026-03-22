from django.core.exceptions import ValidationError
from django.db import models
from config.models import BaseImage
from users.models import User



class Newsletter(models.Model):

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"
        ordering = ['-created_at']

        indexes = [
            models.Index(fields=['status', 'scheduled_at'])
        ]

    STATUS_CHOICES = [
        ('scheduled', 'Запланирована'),
        ('sending', 'Отправляется'),
        ('sent', 'Отправлена'),
        ('failed', 'Ошибка'),
        ('partial', 'Частично отправлена'),
    ]

    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('telegram', 'Telegram'),
        ('both', 'Email + Telegram'),
    ]

    title = models.CharField(max_length=255, verbose_name="Название рассылки")
    message = models.TextField(verbose_name="Текст сообщения")
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        default='both',
        verbose_name="Канал доставки"
    )

    only_paid = models.BooleanField(default=False,
                                    verbose_name="Только оплатившие")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='sending',
        verbose_name="Статус"
    )
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name="Запланирована на")


    total = models.IntegerField(default=0, verbose_name="Всего получателей")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отправки")

    def __str__(self):
        return f"{self.title}"



class NewsletterTask(models.Model):

    class Meta:
        verbose_name = "Задача рассылки"
        verbose_name_plural = "Задачи рассылок"
        ordering = ['channel_sent',]
        unique_together = ['newsletter', 'user']
        indexes = [
            models.Index(fields=['newsletter', 'channel_sent'])]

    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('sent', 'Отправлено'),
        ('failed', 'Ошибка'),
        ('cancelled', 'Отменена')
    ]

    newsletter = models.ForeignKey(
        Newsletter,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Рассылка"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='newsletter_tasks',
        verbose_name="Пользователь"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Статус"
    )

    channel_sent = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Через какой канал отправлено",
        choices=Newsletter.CHANNEL_CHOICES
    )

    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="Сообщение об ошибке"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отправки")

    def __str__(self):
        return f"{self.newsletter.title} -> {self.user.username} ({self.get_status_display()})"

class NewsletterImage(BaseImage):
    image = models.ImageField(
        null=True,
        upload_to='newsletters/',
    )

    newsletter = models.ForeignKey(
        Newsletter,
        related_name='images',
        on_delete=models.CASCADE,
    )


    def clean(self):
        if not self.pk and self.newsletter.images.count() >= 2:
            raise ValidationError("Максимум 2 фото")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
