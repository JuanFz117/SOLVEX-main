"""
Vistas del módulo de tickets - Refactorizado siguiendo el patrón Fat Models, Thin Views.
Toda la lógica de negocio se ha movido a models.py.
"""
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from typing import Any

from .forms import TicketsForm, ComentarioForm
from .models import Tickets, Ticket_prioridad, Ticket_comentarios
from apps.usuario.models import Usuario
from apps.usuario.views import _send_admin_dashboard_update


# ============================================
# Helpers
# ============================================

def get_paginated_queryset(queryset: Any, request, per_page: int = 4) -> tuple:
    """Helper para paginar un queryset."""
    paginator = Paginator(queryset, per_page)
    pagina = request.GET.get("page") or 1
    posts = paginator.get_page(pagina)
    current_page = int(pagina)
    paginas = range(1, posts.paginator.num_pages + 1)
    return posts, current_page, paginas


# ============================================
# Vistas de Colaborador
# ============================================

@login_required
def index(request):
    """Vista principal para crear tickets."""
    usuario_actual = request.user
    
    # Usar el manager optimizado con select_related
    tickets_abiertos = Tickets.objects.abiertos_por_usuario(usuario_actual)
    posts, current_page, paginas = get_paginated_queryset(tickets_abiertos, request, per_page=4)
    
    if request.method == 'POST':
        form = TicketsForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.usuario = usuario_actual
            ticket.save()
            
            # Usar método del modelo para preparar datos WebSocket
            ticket_data_for_ws = ticket.preparar_datos_para_websocket()
            _send_admin_dashboard_update('general', 'new_ticket_notification', ticket_data_for_ws)
            
            return redirect(f"{reverse('tickets:index')}?success_message=Ticket creado exitosamente. revise Tickets Abiertos.")
    else:
        form = TicketsForm()
    
    id_prioridad = Ticket_prioridad.objects.all()
    
    return render(request, 'index.html', {
        'form': form,
        'posts': posts,
        'paginas': paginas,
        'current_page': current_page,
        'colaborador': usuario_actual,
        'id_prioridad': id_prioridad,
        'opciones_soporte': Tickets.get_opciones_soporte(),
        'campos_tabla': Tickets.TICKET_ABIERTO_HEADERS
    })


@login_required
def tickets_page(request):
    """Vista para la página de tickets resueltos."""
    usuario_actual = request.user
    
    tickets_cerrados = Tickets.objects.cerrados_por_usuario(usuario_actual)
    posts, current_page, paginas = get_paginated_queryset(tickets_cerrados, request, per_page=4)
    
    return render(request, 'tickets.html', {
        'posts2': posts,
        'paginas2': paginas,
        'current_page2': current_page,
        'colaborador': usuario_actual,
        'tickets_generales2': Tickets.TICKET_CERRADO_HEADERS
    })


@login_required
@user_passes_test(lambda u: u.es_colaborador, login_url='login')
def ticket_detalle(request, id: int):
    """Vista para mostrar el detalle de un ticket."""
    usuario_actual = request.user
    ticket = get_object_or_404(Tickets.objects.con_comentarios(), id=id, usuario=usuario_actual)
    
    return render(request, 'ticket_detail.html', {
        'colaborador': usuario_actual,
        'ticket': ticket,
        'comentarios': ticket.Comentarios.all().order_by('hora_comentario'),
        'tickets_generales3': Tickets.TICKET_DETALLE_HEADERS
    })


# ============================================
# Vistas de Administrador
# ============================================

@login_required
@user_passes_test(lambda u: u.es_admin_o_superadmin, login_url='login')
def admin_ticket_detail(request, ticket_id: int):
    """
    Vista para que el administrador vea el detalle y chat de un ticket.
    Permite al administrador añadir comentarios.
    """
    ticket = get_object_or_404(Tickets.objects.con_comentarios(), pk=ticket_id)
    admin_user = request.user
    es_superadmin = admin_user.es_superadmin_tipo
    
    can_comment = ticket.id_estado == 'en_progreso' and ticket.asignado_a == admin_user
    
    if request.method == 'POST':
        if can_comment:
            form = ComentarioForm(request.POST, request.FILES)
            if form.is_valid():
                nuevo_comentario = form.save(commit=False)
                nuevo_comentario.id_ticket = ticket
                nuevo_comentario.autor = admin_user
                nuevo_comentario.save()
                return redirect(f"{reverse('tickets:admin_ticket_detail', kwargs={'ticket_id': ticket.id})}?success_message=Comentario añadido con éxito.")
            messages.error(request, "Error al añadir el comentario.")
        else:
            messages.error(request, "No puedes comentar este ticket si no lo has tomado.")
            return redirect('tickets:admin_ticket_detail', ticket_id=ticket.id)
    else:
        form = ComentarioForm()
    
    return render(request, 'admin/chat_admin.html', {
        'ticket': ticket,
        'comentarios': ticket.Comentarios.all().order_by('hora_comentario'),
        'admin_user': admin_user,
        'es_superadmin': es_superadmin,
        'can_comment': can_comment,
        'tickets_generales': Tickets.TICKET_DETALLE_HEADERS,
        'comment_form': form
    })