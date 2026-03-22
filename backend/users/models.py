from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-is_registered', '-paid', 'is_superuser']

    telegram_chat_id = models.BigIntegerField(null=True, blank=True, verbose_name="Chat ID для рассылок", unique=True)
    email = models.EmailField(null=True, blank=True, verbose_name="Email", default=None)
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Номер телефона")
    extras = models.JSONField(default=dict, blank=True)
    paid = models.BooleanField(default=False, verbose_name="Оплачен взнос")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата оплаты")
    registration_step = models.ForeignKey('bot.RegistrationStep', null=True, blank=True, on_delete=models.SET_NULL)
    is_registered = models.BooleanField(default=False, verbose_name="Зарегистрирован")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")

    def __str__(self):
        return f"{self.first_name or self.username} (@{self.username or 'unknown'})"

    def save(self, *args, **kwargs):
        if not self.email:
            self.email = None
        super().save(*args, **kwargs)

    def mark_as_paid(self):
        self.paid = True
        self.paid_at = timezone.now()
        self.save()