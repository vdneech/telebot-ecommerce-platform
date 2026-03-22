from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import User



@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Админка для кастомного пользователя"""

    fieldsets = (
        ('Telegram', {'fields': ('username', 'telegram_chat_id')}),
        ('Регистрация', {'fields': ('is_registered', 'registration_step')}),
        ('Личная информация', {'fields': (
            'first_name', 'last_name', 'phone',
            'email',
            'extras',
        )}),
        ('Статус платежа', {'fields': ('paid', 'paid_at')}),
    )

    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'is_registered',
        'registration_step',
        'paid',
        'extras_preview',
        'created_at',
    ]

    list_filter = ['is_registered', 'paid', 'created_at', 'paid_at']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'telegram_chat_id', ]
    readonly_fields = ['created_at', ]

    # удобно для ForeignKey (RegistrationStep)
    autocomplete_fields = ('registration_step',)

    @admin.display(description='Extras')
    def extras_preview(self, obj: User):
        """
        Короткий превью JSON, чтобы list_display не превращался в простыню.
        """
        data = obj.extras or {}
        if not isinstance(data, dict) or not data:
            return '—'
        keys = list(data.keys())[:3]
        tail = ' …' if len(data.keys()) > 3 else ''
        return ', '.join(str(k) for k in keys) + tail
