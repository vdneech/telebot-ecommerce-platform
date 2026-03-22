from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import User

_USER_COMMON_FIELDS = [
    'id',
    'username',
    'email',
]

class UserBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = _USER_COMMON_FIELDS
        read_only_fields = _USER_COMMON_FIELDS

class UserSerializer(UserBaseSerializer):
    class Meta(UserBaseSerializer.Meta):
        fields = _USER_COMMON_FIELDS + [
            'is_superuser', 'first_name', 'last_name',
            'telegram_chat_id', 'phone', 'extras',
            'paid', 'paid_at', 'is_registered',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'is_superuser']

class TokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        return token