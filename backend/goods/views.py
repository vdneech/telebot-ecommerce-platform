from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from config.utils import UploadImageMixin
from goods.models import Good, GoodImage
from goods.serializers import GoodSerializer, GoodImageSerializer
import logging

logger = logging.getLogger('gfs')

class GoodViewSet(UploadImageMixin, viewsets.ModelViewSet):

    image_serializer_class = GoodImageSerializer
    image_relation_field = 'good'

    serializer_class = GoodSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = Good.objects.all()
        return queryset.prefetch_related("images").order_by('-available')

    @action(detail=True, methods=['post'], url_path='upload-image')
    def upload_image(self, request, pk=None):
        good = self.get_object()
        serializer = GoodImageSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(good=good)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GoodImageViewSet(viewsets.ModelViewSet):
    serializer_class = GoodImageSerializer

    def get_queryset(self):
        return GoodImage.objects.all().order_by("-is_invoice")

    @action(detail=True, methods=['patch'], url_path='set-as-invoice')
    def set_as_invoice(self, request, pk=None):
        """Сделать это фото инвойс‑фото и сбросить флаг у остальных фото товара."""
        image = self.get_object()
        image.is_invoice = True
        image.save()

        serializer = self.get_serializer(image)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        good = instance.good
        was_invoice = instance.is_invoice

        # 1. Удаляем само изображение
        instance.delete()

        if was_invoice:
            next_image = good.images.first()
            if next_image:
                next_image.is_invoice = True
                next_image.save(update_fields=['is_invoice'])