import csv
import logging
from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from bot.models import RegistrationStep
from users.models import User
from users.serializers import UserSerializer

logger = logging.getLogger('gfs')

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.order_by('-is_registered', '-paid', 'is_superuser')

    @action(detail=False, methods=['post'], url_path='clean-registrations')
    @transaction.atomic
    def clean_registrations(self, request):
        queryset = self.get_queryset()
        count = queryset.update(
            is_registered=False,
            registration_step=None,
            paid=False,
            paid_at=None
        )

        logger.warning(f"Registrations cleaned by admin. User_id: {request.user.id}, Count: {count}")

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='clean-payments')
    @transaction.atomic
    def clean_payments(self, request):
        queryset = self.get_queryset()
        count = queryset.update(
            paid=False,
            paid_at=None
        )

        logger.warning(f"Payments cleaned by admin. User_id: {request.user.id}, Count: {count}")
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='csv')
    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')

        steps = RegistrationStep.objects.filter(field_type='text').order_by('order')
        extras_keys = [step.field_name for step in steps]

        writer.writerow([
            'Telegram',
            'Email',
            'Оплата',
            'Дата оплаты',
            'Дата регистрации'
        ] + extras_keys)

        total_count = 0
        paid_count = 0

        for user in self.get_queryset().iterator():
            total_count += 1
            if user.paid:
                paid_count += 1

            row = [
                user.username,
                user.email,
                'Да' if user.paid else 'Нет',
                user.paid_at.strftime('%Y-%m-%d %H:%M') if user.paid and user.paid_at else '',
                user.created_at.strftime('%Y-%m-%d') if user.created_at else '',
            ]

            user_extras = user.extras or {}
            for key in extras_keys:
                row.append(user_extras.get(key, ''))

            writer.writerow(row)

        writer.writerow([])
        writer.writerow(['Всего пользователей', 'Оплативших'])
        writer.writerow([total_count, paid_count])

        logger.info(f"Exported CSV. User_id: {request.user.id}, Total count: {total_count}")
        
        return response