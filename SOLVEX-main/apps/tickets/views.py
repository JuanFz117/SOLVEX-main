from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import TicketsForm, ComentarioForm
from .models import Tickets, Ticket_prioridad, Ticket_comentarios
from apps.usuario.models import Usuario
from apps.usuario.views import _send_admin_dashboard_update  # FUNCION DE ENVIO A ADMIN
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse

#-------------------------------------------#

# FUNCION DE VISTA PRINCIPAL

def es_colaborador(user):
    return user.is_authenticated and user.rol == Usuario.ROLE_CHOICES[2][0] # 'colaborador'

def es_admin_o_superadmin(user):
    return user.is_authenticated and (user.rol == Usuario.ROLE_CHOICES[1][0] or user.rol == Usuario.ROLE_CHOICES[0][0]) # 'admin' or 'superadmin'

def es_superadmin(user):
    """Check if a user has superadmin role."""
    # VALIDAR QUE COINCIDAN LOS ROLES
    return user.is_authenticated and user.rol == 'superadmin'

@login_required  # SOLO USUARIOS LOGUEADOS
def index(request):
    """
    Vista principal para crear tickets.
    """
    # OBTENER EL USUARIO REGISTRADO
    usuario_actual = request.user
    tickets_abiertos = Tickets.objects.filter(Q(id_estado="abierto" ) | Q(id_estado="en_progreso"), usuario_id=usuario_actual)
    
    paginator = Paginator(tickets_abiertos, 4) # PAGINACIÓN DE 4 PARA QUE NO SEA TAN LARGA LA LISTA
    pagina = request.GET.get("page") or 1 # SE LE ASIGNA LA PAGINA ACTUAL O EL 1
    posts = paginator.get_page(pagina) # SE GUARDA LA PAGINA EN POST
    current_page = int(pagina) # OBTIENE LA PAGINA ACTUAL
    paginas = range(1, posts.paginator.num_pages + 1)

    # PROCESAR EL FORMULARIO SI SE ENVIA
    if request.method == 'POST':
        form = TicketsForm(request.POST, request.FILES) # REQUERIR EL ADJUNTO EN EL FORMULARIO
        if form.is_valid(): # ¿EL FORMULARIO ES VALIDO?
            ticket = form.save(commit=False)
            ticket.usuario = usuario_actual  # ASIGNAR EL USUARIO AUTENTICADO AL TICKET.
            ticket.save()  # GUARDAR EL FORMULARIO
            
            #* PREPARAR DATOS DEL TICKET PARA EL WEBSOCKET
            ticket_data_for_ws = {
                'id': ticket.id,
                'motivo': ticket.motivo,
                'usuario_username': ticket.usuario.username,
                'tipo_soporte': ticket.tipo_soporte,
                'estado_display': ticket.get_id_estado_display(),
                'estado_value': ticket.id_estado,
                'prioridad_display': ticket.get_id_prioridad_display(), # ej: "Alta"
                'prioridad_value': ticket.id_prioridad, # ej: "alta"
                'fecha_creacion': ticket.fecha_creacion.isoformat(),
                'url_detalle_admin': reverse('tickets:admin_ticket_detail', kwargs={'ticket_id': ticket.id})
            }
            #* ENVIAR LA NOTIFICACIÓN AL GRUPO GENERAL DE ADMINISTRADORES
            _send_admin_dashboard_update('general', 'new_ticket_notification', ticket_data_for_ws)

            success_url = reverse('tickets:index')  + '?success_message=Ticket creado exitosamente. revise Tickets Abiertos.' #
            return redirect(success_url)  # Redirige a /inicio/ después de guardar
    else:
        form = TicketsForm()
        
    # Obtener las prioridades y opciones de soporte para el formulario.
    id_prioridad = Ticket_prioridad.objects.all()
    
    opciones_soporte =  { # Las opciones de soporte deberían ser cargadas desde la base de datos para mayor flexibilidad
        'Tipo_de_Soporte': {
            'Soporte Técnico': 'Soporte Técnico',
            'Soporte Operativo': 'Soporte Operativo',
            'Área de Desarrollo': 'Área de Desarrollo'
        },
        'Agencia_Corresponsal': {
            'No Aplica': 'No Aplica',
            'Agencia Principal': 'Agencia Principal',
            'Agencia Popular': 'Agencia Popular',
            'Agencia Catama': 'Agencia Catama',
            'Agencia Porfía': 'Agencia Porfía',
            'Agencia Montecarlo': 'Agencia Montecarlo',
            'Agencia Acacías': 'Agencia Acacías',
            'Agencia Vistahermosa': 'Agencia Vistahermosa',
            'Agencia Guayabetal': 'Agencia Guayabetal',
            'Agencia Barranca de Upía': 'Agencia Barranca de Upía',
            'Agencia Cabuyaro': 'Agencia Cabuyaro',
            'Agencia Puerto Gaitán': 'Agencia Puerto Gaitán',
            'Corresponsal Puerto López': 'Corresponsal Puerto López',
            'Corresponsal El Castillo': 'Corresponsal El Castillo',
            'Corresponsal Lejanías': 'Corresponsal Lejanías',
            'Corresponsal Puerto Lleras': 'Corresponsal Puerto Lleras',
            'Corresponsal Puerto Rico': 'Corresponsal Puerto Rico',
            'Corresponsal Cumaral': 'Corresponsal Cumaral',
            'Corresponsal Mesetas': 'Corresponsal Mesetas',
            'Corresponsal Uribe': 'Corresponsal Uribe',
            'Corresponsal Yopal': 'Corresponsal Yopal',
            'Corresponsal Villanueva': 'Corresponsal Villanueva'
        },
        'Administrativa': {
            'No Aplica':'No Aplica',
            'Gerencia General': 'Gerencia General',
            'Gerencia Innovación y Transformación': 'Gerencia Innovación y Transformación',
            'Gerencia Comercial': 'Gerencia Comercial',
            'Oficial de Cumplimiento': 'Oficina de Cumplimiento',
            'Oficial de Riesgo': 'Oficial de Riesgo',
            'Servicios Administrativos': 'Servicios Administrativos',
            'Talento Humano': 'Talento Humano',
            'Operaciones': 'Operaciones',
            'Contabilidad': 'Contabilidad',
            'Revisoría': 'Revisoría',
            'Auditoria': 'Auditoria',
            'Credito': 'Credito',
            'Cartera': 'Cartera',
            'Cobranza': 'Cobranza',
            'Garantías': 'Garantías',
            'Comunicaciones': 'Comunicaciones',
            'Convenios': 'Convenios',
            'Canales': 'Canales',
        },
    }
    campos_tabla = [
        'ID',
        'Motivo',
        'Tipo de Soporte',
        'Estado',
        'Prioridad',
        'Fecha de Creación'
        ]

    return render(request, 'index.html', {
        'form': form,
        'posts': posts, # Enviar solo la página actual de tickets
        'paginas': paginas,
        'current_page': current_page,
        'colaborador': usuario_actual, # Pasamos el nuevo objeto porque actualizamos el modelo
        'id_prioridad': id_prioridad,
        'opciones_soporte': opciones_soporte,
        'campos_tabla': campos_tabla
    })

# FUNCION DE VISTA DE TICKETS RESUELTOS ( HISTORIAL )

@login_required  # Solo usuarios autenticados pueden acceder a esta vista.
def tickets_page(request):
    """
    Vista para la página de tickets resueltos.
    """
    # Obtenemos el usuario que se encuentra registrado
    usuario_actual = request.user
    # Traemos todos los tickets del usuario solo los cerrados
    tickets_cerrados = Tickets.objects.filter(usuario_id=usuario_actual, id_estado="cerrado")

    tickets_generales2 = [
        'ID',
        'Motivo',
        'Tipo de Soporte',
        'Estado',
        'Fecha de Creación',
        'Fecha de Solución'
    ]
    
    paginator2 = Paginator(tickets_cerrados, 4) # Creamos la paginación con 4 campos maximo de la sección tickets abiertos
    pagina2 = request.GET.get("page") or 1 # Se le asigna la página actual o el 1
    posts2 = paginator2.get_page(pagina2) # Se guarda la página en posts
    current_page2 = int(pagina2) # Obtiene la página actual
    paginas2 = range(1, posts2.paginator.num_pages + 1)
    
    return render(request, 'tickets.html', {
        'posts2': posts2,  # Enviar solo la página actual de tickets cerrados
        'paginas2': paginas2,
        'current_page2': current_page2,
        'colaborador': usuario_actual, # Pasamos el nuevo objeto porque actualizamos el modelo
        'tickets_generales2': tickets_generales2
    })

@login_required
@user_passes_test(es_colaborador, login_url='login') # Protege la vista
def ticket_detalle(request, id):
    """
    VISTA PARA MOSTRAR EL DETALLE DEL TICKET Y PODER SABER RESPUESTA DEL ADMINISTRADOR
    """
    
    usuario_actual = request.user # Obtenemos el usuario que se encuentra registrado

    ticket = get_object_or_404(Tickets, id=id, usuario=usuario_actual)
    comentarios = ticket.Comentarios.all().order_by('hora_comentario')

    tickets_generales = [
        'ID',
        'Tipo de Soporte',
        'Area reportada',
        'Estado',
        'Prioridad',
        'Fecha de Creación'
    ]
    
    return render(request, 'ticket_detail.html', {
        'colaborador': usuario_actual,
        'ticket': ticket,
        'comentarios': comentarios,
        'tickets_generales3': tickets_generales,
        })

# --- VISTAS PARA LOS ADMINISTRADORES --- #


@login_required
@user_passes_test(es_admin_o_superadmin, login_url='login') # Protege la vista
def admin_ticket_detail(request, ticket_id):
    """
    Vista para que el administrador vea el detalle y chat de un ticket.
    Permite al administrador añadir comentarios.
    """

    ticket = get_object_or_404(Tickets, pk=ticket_id) 
    admin_user = request.user # Obtenemos el usuario que se encuentra registrado

    es_superadmin = request.user.rol == 'superadmin' # Verifica si el usuario es superadmin

    # Determinar si el admin actual puede comentar
    # Puede comentar si el ticket está en progreso Y asignado a él.
    can_comment = False 
    if ticket.id_estado == 'en_progreso' and ticket.asignado_a == admin_user:
        can_comment = True

    if request.method == 'POST':
        # La lógica de POST para comentarios ahora se maneja a través de WebSockets (consumers.py).
        if can_comment: # Solo procesar el formulario si puede comentar
            form = ComentarioForm(request.POST, request.FILES)
            if form.is_valid():
                nuevo_comentario = form.save(commit=False)
                nuevo_comentario.id_ticket = ticket
                nuevo_comentario.autor = admin_user # El autor es el admin logueado
                nuevo_comentario.save()
                success_url = reverse('tickets:admin_ticket_detail', kwargs={'ticket_id': ticket.id}) + '?success_message=Comentario añadido con éxito.'
                return redirect(success_url)
            else:
                messages.error(request, "Error al añadir el comentario.")
        else:
            messages.error(request, "No puedes comentar este ticket si no lo has tomado.")
            return redirect('tickets:admin_ticket_detail', ticket_id=ticket.id)
    else:
        form = ComentarioForm() # Formulario vacío para GET

    tickets_generales = [
        'ID', # Estos campos deberían estar definidos en el modelo o como una constante global
        'Tipo de Soporte',
        'Area reportada',
        'Estado',
        'Prioridad',
        'Fecha de Creación'
    ]
    context = {
        'ticket': ticket,
        'comentarios': ticket.Comentarios.all().order_by('hora_comentario'), # Pasa los comentarios ordenados
        'admin_user': admin_user,  # Usuario autenticado
        'es_superadmin': es_superadmin,  # Verifica si el usuario es superadmin
        'can_comment': can_comment, # Indica si el admin puede comentar
        'tickets_generales': tickets_generales, # Pasa los encabezados de la tabla
        'comment_form': form,       # Pasa el formulario de comentario para mostrar errores si los hay
    }
    # Renderiza una plantilla específica para el chat de admin o reutiliza/adapta una existente
    return render(request, 'admin/chat_admin.html', context) # Usa la plantilla chat_admin.html