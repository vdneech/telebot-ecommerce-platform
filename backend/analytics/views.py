
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import User
from goods.models import Good


class UsersAnalyticsAPIView(APIView):
    def get(self, request):
        stats = User.objects.aggregate(
            total_users = Count('telegram_chat_id'),
            paid_users = Count('telegram_chat_id', filter=Q(paid=True))
        )

        import datetime
        thirty_days_ago = timezone.now().date() - datetime.timedelta(days=30)

        daily_stats = User.objects.filter(
            created_at__date__gte=thirty_days_ago
        ).annotate(
            day=TruncDate('created_at')
        ).values('day').annotate(
            registrations=Count('telegram_chat_id'),
            paid_registrations=Count('telegram_chat_id', filter=Q(paid=True))
        ).order_by('day')

        return Response({
            "total_users": stats['total_users'],
            "paid_users": stats['paid_users'],
            "daily_stats": list(daily_stats)
        })