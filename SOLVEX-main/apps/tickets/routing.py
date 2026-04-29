# apps/tickets/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/ticket/(?P<ticket_id>\d+)/chat/$', consumers.TicketChatConsumer.as_asgi()),
    re_path(r'ws/admin_dashboard/$', consumers.AdminDashboardConsumer.as_asgi()),
]