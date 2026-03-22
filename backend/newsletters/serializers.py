from django.utils import timezone
from rest_framework import serializers
from newsletters.models import Newsletter, NewsletterTask, NewsletterImage
from users.serializers import UserBaseSerializer


class NewsletterImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterImage
        fields = ['id', 'image']
        read_only_fields = ['id']

    def validate(self, attrs):
        newsletter = attrs.get('newsletter') or (self.instance.newsletter if self.instance else None)

        if newsletter:

            queryset = newsletter.images.all()

            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.count() >= 2:
                raise serializers.ValidationError(
                    "Для одной рассылки можно загрузить не более 2 фотографий."
                )
        return attrs


class NewsletterTaskSerializer(serializers.ModelSerializer):
    """Сериализатор для задач рассылок"""

    user = UserBaseSerializer()

    class Meta:
        model = NewsletterTask
        fields = [
            'id', 'user', 'status',
            'channel_sent', 'error_message', 'sent_at'
        ]
        read_only_fields = ['id', 'sent_at']


_NEWSLETTER_BASE_FIELDS = [
    'id', 'title', 'channel', 'status',
    'scheduled_at'
]


class NewsletterProgressSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Newsletter
        fields = ['id', 'progress']
        read_only_fields = ['__all__']

    def get_progress(self, obj):
        total = obj.tasks.count() or 1
        sent = obj.tasks.filter(status='sent').count()

        progress = sent / total * 100

        if obj.status in ['sent', 'partial']:
            progress = 100
        return progress




class NewsletterBaseSerializer(NewsletterProgressSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Newsletter
        fields = _NEWSLETTER_BASE_FIELDS + ['progress', 'image']

        read_only_fields = ['__all__']

    def get_image(self, obj):
        if obj.images.all():
            return obj.images.first().image.url
        return None


class NewsletterSerializer(NewsletterBaseSerializer):
    tasks = NewsletterTaskSerializer(many=True, read_only=True)
    images = NewsletterImageSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    sent = serializers.SerializerMethodField()
    failed = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()

    class Meta:
        model = Newsletter
        fields = _NEWSLETTER_BASE_FIELDS + [
            'message',
            'total',
            'sent',
            'failed',
            'only_paid',
            'sent_at',
            'tasks',
            'images',
            'progress'

        ]
        read_only_fields = [
            'id', 'failed_count', 'total_recipients', 'sent_at',
            'total', 'sent', 'failed', 'progress'
        ]

    def get_total(self, obj):
        total = obj.tasks.count()
        return total

    def get_sent(self, obj):
        sent = obj.tasks.filter(status='sent').count()
        return sent

    def get_failed(self, obj):
        failed = obj.tasks.filter(status='failed').count()
        return failed

    def get_message(self, obj):
        message = obj.message.replace('\n', '<br>')
        return message


class NewsletterCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Newsletter
        fields = [
            'id',
            'title', 'message', 'channel',
            'only_paid',
            'scheduled_at',
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        scheduled_at = attrs.get('scheduled_at')
        if scheduled_at is None:
            return attrs

        now = timezone.now()
        if scheduled_at < now:
            raise serializers.ValidationError({
                'detail': 'Нельзя отправить рассылку в прошлое',
            })

        return attrs
