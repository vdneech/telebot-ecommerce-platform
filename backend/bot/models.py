import datetime
import json
from decimal import Decimal

from PIL.ImtImagePlugin import field
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, MinValueValidator, MaxValueValidator
from django.db import models
import re

from users.models import User


class ConfigurationManager(models.Manager):
    """Удобный доступ к конфигурации с кешем"""

    _cache = None

    def get_config(self) -> 'Configuration':
        """Возвращает единственную конфигурацию (кеширует)"""
        return self.first()


class Configuration(models.Model):

    INVOICE_PAYLOAD = 'registration'

    class Meta:
        verbose_name = verbose_name_plural = 'Конфигурация бота'

    max_users = models.PositiveSmallIntegerField(default=100)


    price = models.DecimalField(max_digits=10,
        decimal_places=2,
        verbose_name="Цена в рублях",
        default=1000,
        validators=[
            MinValueValidator(69),
            MaxValueValidator(15000)
        ])

    invoice_label = models.CharField(max_length=100, default='Регистрация на мероприятие', null=False)
    invoice_title = models.CharField(max_length=100, default='Регистрация на мероприятие', null=False)
    invoice_description = models.CharField(max_length=100, default='Описание регистрации', null=False)
    invoice_image = models.ImageField(
        upload_to='invoices/',
        null=True,
        blank=True,
        verbose_name='Фото инвойса'
    )

    end_of_registration = models.DateField(null=True, blank=True)

    start_message = models.TextField(default='Start message')
    merchant_message = models.TextField(default='Merchants')
    ceo_message = models.TextField(default='CEOs')
    format_message = models.TextField(default='Format message')
    already_registered_message = models.TextField(default='Already registered')
    closed_registrations_message = models.TextField(default='Registrations are closed')

    objects = ConfigurationManager()

    def save(self, *args, **kwargs):
        """Сохранение только исходной записи"""
        super().save(*args, **kwargs)

        duplicates = Configuration.objects.exclude(id=self.id)
        duplicates.delete()

    def delete(self, *args, **kwargs):
        """Запрет на удаление конфигурации"""
        raise ValueError("Global Configuration can't be deleted")

    def __str__(self):
        return f"Configuration"

    @property
    def provider_data(self):
        price = self.price

        if isinstance(price, Decimal):
            price_str = f'{price:.2f}'
        else:
            price_str = str(price)

        return json.dumps({
            "receipt": {
                "items": [{
                    "description": self.invoice_description,
                    "quantity": 1.00,
                    "amount": {"value": price_str, "currency": "RUB"},
                    "vat_code": 1,
                }]
            },
            "amount": {"value": price_str, "currency": "RUB"},
        })


class RegistrationStep(models.Model):
    class Meta:
        verbose_name = 'Шаг регистрации'
        verbose_name_plural = 'Шаги регистрации'

    FIELD_TYPES = [
        ('text', 'Текст'),
        ('email', 'Email'),
        ('phone', 'Телефон'),
        ('fullname', 'ФИО'),
        ('date', 'Дата'),
    ]

    order = models.PositiveSmallIntegerField(verbose_name='Порядковый номер')
    message_text = models.TextField(verbose_name='Текст сообщения')
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, verbose_name='Тип поля')
    field_name = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name='Имя поля')
    error_message = models.TextField(default='Некорректные данные', verbose_name='Текст ошибки')

    next_step = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='prev_steps',
        verbose_name='Следующий шаг'
    )

    def __str__(self):
        return f'Шаг {self.order}'

    def validate_data(self, raw: str):
        """
        Возвращает:
          (True, cleaned_value)  - если валидно
          (False, error_message) - если нет
        """
        raw = (raw or "").strip()

        # required по умолчанию (у тебя is_required убран — если добавишь, учти его)
        if not raw:
            return False, "Это поле обязательно для заполнения"

        try:
            if self.field_type == "text":
                return True, raw

            if self.field_type == "email":
                # Django validate_email бросает ValidationError при невалидном email [web:202]
                validate_email(raw)
                return True, raw.lower()

            if self.field_type == "phone":
                # Если пришёл contact.phone_number, он может быть в разных форматах.
                # Нормализуем: оставляем + и цифры
                cleaned = re.sub(r"[^\d+]", "", raw)

                # Простейшая проверка длины; можно усилить regex'ом
                # Пример международного формата: +79991234567
                if len(re.sub(r"[^\d]", "", cleaned)) < 10:
                    return False, self.error_message

                return True, cleaned

            if self.field_type == "number":
                # Можно вернуть float или строку — зависит от того, куда пишешь.
                # Если в user поле IntegerField — лучше int
                # Если DecimalField — лучше Decimal
                try:
                    value = float(raw.replace(",", "."))
                except ValueError:
                    return False, self.error_message
                return True, value

            if self.field_type == "fullname":
                parts = [p for p in raw.split() if p]
                if len(parts) < 2:
                    return False, self.error_message
                # Нормализуем пробелы
                return True, " ".join(parts)

            if self.field_type == "date":
                # Поддержим несколько форматов: 2026-01-22, 22.01.2026, 22/01/2026
                for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                    try:
                        d = datetime.strptime(raw, fmt).date()
                        return True, d
                    except ValueError:
                        pass
                return False, self.error_message

            return False, "Неизвестный тип поля"

        except ValidationError:
            return False, self.error_message

    def save_to_user(self, user, value):
        """
        value — то, что вернул validate_data на success:
        - email/text/fullname/phone -> str
        - number -> float или int
        - date -> datetime.date
        """
        update_fields = []

        if self.field_type == "fullname":
            parts = [p for p in str(value).split() if p]
            if len(parts) < 2:
                raise ValidationError("Некорректное ФИО")

            user.first_name = parts[0]
            user.last_name = " ".join(parts[1:])
            update_fields += ["first_name", "last_name"]


        elif self.field_type == "email":

            try:



                validate_email(value)

                cleaned = str(value).strip().lower()

                setattr(user, self.field_type, cleaned)

                update_fields.append(self.field_type)

            except ValidationError:
                raise ValueError(f"Невалидный email: {value}")


        elif self.field_type == "phone":
            cleaned = re.sub(r"[^\d+]", "", str(value))
            setattr(user, self.field_type, cleaned)
            update_fields.append(self.field_type)


        elif self.field_type == 'text':

            if not self.field_name:
                raise ValueError("field_name не задан для типа text")

            extras = user.extras or {}

            extras[self.field_name] = value

            user.extras = extras

            update_fields.append('extras')

        user.save(update_fields=update_fields)


