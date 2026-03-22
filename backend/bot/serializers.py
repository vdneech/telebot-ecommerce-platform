from django.core.files.images import get_image_dimensions
from rest_framework import serializers

from bot.models import Configuration, RegistrationStep


class ConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        fields = '__all__'

    def validate_invoice_image(self, value):
        if value:
            
            width, height = get_image_dimensions(value)
            expected_ratio = 1
            actual_ratio = width / height

            if abs(actual_ratio - expected_ratio) > 0.02:
                raise serializers.ValidationError(
                    f"Изображение должно иметь соотношение сторон 1:1 (сейчас {width}x{height})"
                )
        return value


class RegistrationStepSerializer(serializers.ModelSerializer):
    field_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, )

    class Meta:
        model = RegistrationStep
        fields = [
            'id', 'order', 'message_text', 'field_type', 'field_name',
            'error_message',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        '''Валидация на текстовый тип: field_name обязателен для field_type'''
        field_type = attrs.get('field_type')
        field_name = attrs.get('field_name')

        if field_type == 'text' and not field_name:
            raise serializers.ValidationError({
                'Название поля': 'Это поле обязательно для выбранного типа'
            })

        if field_type != 'text':

            if not self.instance:
                exists = RegistrationStep.objects.filter(field_type=field_type).exists()
                if exists:
                    raise serializers.ValidationError({
                        'Тип поля': f'Шаг с таким типом уже существует. Можно создать только один шаг каждого типа, кроме текстовых.'
                    })

        return attrs


class RegistrationStepReorderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order = serializers.IntegerField(min_value=1)

