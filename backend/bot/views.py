import json
import os
import logging
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from django.db.models import F
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.views import APIView
from telebot.types import Update

from bot.models import Configuration, RegistrationStep
from bot.serializers import ConfigurationSerializer, RegistrationStepSerializer, RegistrationStepReorderSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from bot.bot import bot

logger = logging.getLogger('gfs')


class ConfigurationAPIView(APIView):
    parser_classes = [MultiPartParser, JSONParser]

    def get(self, request):
        config = Configuration.objects.get_config()
        serializer = ConfigurationSerializer(config)
        return Response(serializer.data)

    def patch(self, request):
        config = Configuration.objects.get_config()


        data = request.data.copy()
        if 'invoice_image' in data and (data['invoice_image'] == '' or data['invoice_image'] == 'null'):
            if config.invoice_image:
                config.invoice_image.delete(save=False)
            config.invoice_image = None

        serializer = ConfigurationSerializer(config, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def post(self, request):
        """Алиас для patch, если фронт шлет POST с файлом"""
        return self.patch(request)


class RegistrationStepViewSet(viewsets.ModelViewSet):
    queryset = RegistrationStep.objects.all()
    serializer_class = RegistrationStepSerializer

    def perform_create(self, serializer):

        FIELD_TYPE_NAMES = {
            'email': 'Email',
            'phone': 'Телефон',
            'fullname': 'ФИО',
            'date': 'Дата',
        }

        field_type = serializer.validated_data.get('field_type')

        try:
            if field_type and field_type != 'text':
                field_name = FIELD_TYPE_NAMES.get(field_type)
                serializer.save(field_name=field_name)
            else:
                serializer.save()
        except IntegrityError:
            raise ValidationError({
                'field_name': 'Шаг с таким названием уже существует'
            })

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        '''Переупорядочивание шагов'''

        serializer = RegistrationStepReorderSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data

        if not items:
            return Response({'error': 'No items provided'}, status=HTTP_400_BAD_REQUEST)

        ids = [x["id"] for x in items]
        orders = [x["order"] for x in items]

        if len(ids) != len(set(ids)):
            return Response({"detail": "Duplicate ids"}, status=HTTP_400_BAD_REQUEST)

        if len(orders) != len(set(orders)):
            return Response({"detail": "Duplicate orders"}, status=HTTP_400_BAD_REQUEST)

        steps = RegistrationStep.objects.select_related('next_step').filter(id__in=ids)
        step_map = {s.id: s for s in steps}

        missing = [i for i in ids if i not in step_map]
        if missing:
            return Response({"detail": f"Steps not found: {missing}"}, status=HTTP_400_BAD_REQUEST)

        for item in items:
            step_map[item["id"]].order = item["order"]

        ordered_steps = sorted(steps, key=lambda s: s.order)
        for idx, step in enumerate(ordered_steps):
            step.next_step = ordered_steps[idx + 1] if idx + 1 < len(ordered_steps) else None

        with transaction.atomic():
            RegistrationStep.objects.bulk_update(ordered_steps, ["order", "next_step"])

        return Response({"count": len(ordered_steps)}, status=HTTP_200_OK)


@csrf_exempt
def webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)


    secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    expected_token = os.getenv('WEBHOOK_SECRET')

    if expected_token and secret_token != expected_token:
        logger.warning(f"Unauthorized webhook access attempt. Token mismatch.")
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        body_unicode = request.body.decode('utf-8')
        update_dict = json.loads(body_unicode)
        update = Update.de_json(update_dict)

        bot.process_new_updates([update])

        return JsonResponse({'ok': True})

    except Exception as e:
        logger.error(f'Webhook error: {e}', exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
