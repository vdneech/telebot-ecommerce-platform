from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from goods.provider import generate_provider_data
from users.models import User
from config.models import BaseImage

class Good(models.Model):
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["-available", ]

    quantity = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Количество на складе")

    title = models.CharField(
        max_length=32,
        verbose_name="Название товара"
    )

    label = models.CharField(max_length=255,
                             verbose_name="Название для платежа")

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена в рублях",
        validators=[
            MinValueValidator(69),
            MaxValueValidator(15000)
        ]
    )

    description = models.TextField(null=False,
                                   blank=False,
                                   verbose_name="Описание")

    available = models.BooleanField(default=True,
                                    verbose_name="Доступен ли товар")

    def __str__(self):
        return f"{self.title} - {self.price}₽"

    @property
    def provider_data(self):
        return generate_provider_data(self)


class GoodImage(BaseImage):
    class Meta:
        verbose_name = "Фото товара"
        verbose_name_plural = "Фотографии товара"

    good = models.ForeignKey(Good, on_delete=models.CASCADE, related_name="images", verbose_name="Товар")
    image = models.ImageField(upload_to="goods/")
    is_invoice = models.BooleanField(default=False,
                                     verbose_name="Фото в оплате",
                                     help_text="Если ни одно не отмечено, используется первое из предоставленных")

    def clean(self):
        if not self.pk and self.good.images.count() >= 3:
            raise ValidationError("Максимум 3 фото")

    def save(self, *args, **kwargs):
        self.full_clean()


        if self.is_invoice:
            self.good.images.filter(is_invoice=True).exclude(pk=self.pk).update(is_invoice=False)

        super().save(*args, **kwargs)

class Order(models.Model):
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    good = models.ForeignKey(
        Good,
        related_name="orders",
        verbose_name="Заказы",
        on_delete=models.PROTECT,
    )

    user = models.ForeignKey(
        User,
        related_name="orders",
        verbose_name="Заказы",
        on_delete=models.SET_NULL,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )
