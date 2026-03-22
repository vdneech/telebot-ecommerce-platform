from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils import timezone
from rest_framework.views import APIView

from config.utils import UploadImageMixin
from .tasks import send_newsletter_task

from newsletters.models import Newsletter
from newsletters.serializers import NewsletterCreateSerializer, NewsletterSerializer, NewsletterBaseSerializer, \
    NewsletterImageSerializer, NewsletterProgressSerializer
import logging

logger = logging.getLogger(__name__)



class NewsletterViewSet(UploadImageMixin, viewsets.ModelViewSet):


    image_serializer_class = NewsletterImageSerializer
    image_relation_field = 'newsletter'

    serializer_class = NewsletterSerializer
    queryset = Newsletter.objects.all()


    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = NewsletterBaseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = NewsletterBaseSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = NewsletterCreateSerializer(data=request.data)
        if serializer.is_valid():
            newsletter = Newsletter.objects.create(
                **serializer.validated_data
            )
            if not newsletter.scheduled_at:
                newsletter.status = 'sending'
                send_newsletter_task.apply_async(
                    args=(newsletter.pk,),
                    countdown=5)
            else:
                newsletter.status = 'scheduled'
                newsletter.save()
                send_newsletter_task.apply_async(
                    args=(newsletter.pk,),
                    eta=newsletter.scheduled_at)
            serializer = self.serializer_class(newsletter)


            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='progress')
    def progress(self, request):
        newsletters = Newsletter.objects.all()
        serializer = NewsletterProgressSerializer(newsletters, many=True)
        return Response(serializer.data)


