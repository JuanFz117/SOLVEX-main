from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
from .models import Tickets, Ticket_comentarios, Ticket_estado, Ticket_prioridad#, Usuarios

# admin.site.register(Usuarios, UserAdmin)
admin.site.register(Tickets)
admin.site.register(Ticket_comentarios)
admin.site.register(Ticket_estado)
admin.site.register(Ticket_prioridad)

# Register your models here.
