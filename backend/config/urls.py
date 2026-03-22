from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from analytics.views import UsersAnalyticsAPIView
from goods.views import GoodViewSet, GoodImageViewSet
from newsletters.views import NewsletterViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from users.views import UserViewSet
from bot.views import RegistrationStepViewSet, ConfigurationAPIView, webhook

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'goods', GoodViewSet, basename='goods')
router.register(r'newsletters', NewsletterViewSet, basename='newsletters')
router.register(r'goods/images', GoodImageViewSet, basename='good-images')
router.register(r'bot/registration-steps', RegistrationStepViewSet, basename='bot-registration')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/analytics/users/', UsersAnalyticsAPIView.as_view(), name='users-analytics'),
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('api/bot/config/', ConfigurationAPIView.as_view(), name='config'),

    path('webhooks/', webhook, name='webhook'),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
