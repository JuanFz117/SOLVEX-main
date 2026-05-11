import io
import base64
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

# Configuración para generar gráficos en el servidor sin interfaz gráfica
matplotlib.use('Agg')

# Importación de nuestros modelos refactorizados
from apps.tickets.models import Tickets, TipoSoporte
from apps.usuario.forms import CambiarContraseñaForm # Asegúrate de tener este import correcto

# ==============================================================================
# 1. REDIRECCIÓN CENTRAL
# ==============================================================================

@login_required
def post_login_redirect(request):
    """
    Redirige al usuario tras iniciar sesión utilizando la propiedad 
    'get_dashboard_url' definida inteligentemente en el modelo Usuario.
    """
    return redirect(request.user.get_dashboard_url)


# ==============================================================================
# 2. DASHBOARD DE ADMINISTRADORES (Por Área)
# ==============================================================================

@login_required
@user_passes_test(lambda u: u.es_admin_tipo)
def admin_dashboard(request):
    """
    Dashboard para administradores de área. Solo ven los tickets de su categoría.
    Aprovecha el select_related del manager para evitar el problema N+1.
    """
    usuario = request.user

    # Verificamos que tenga un área de soporte asignada en su perfil
    if not usuario.tiene_categoria:
        messages.error(request, "No tienes un área de soporte asignada para ver el dashboard.")
        return redirect('tickets:index')

    try:
        # Obtenemos el ID real del TipoSoporte en base al nombre guardado en el usuario
        categoria_obj = TipoSoporte.objects.get(nombre=usuario.categoria)
        
        # Llamamos a los métodos limpios del Manager y el Modelo
        tickets = Tickets.objects.abiertos_por_categoria(categoria_obj.id)
        conteos = Tickets.conteos_por_categoria(categoria_obj.id)
        
    except TipoSoporte.DoesNotExist:
        messages.error(request, "El área de soporte asignada a tu perfil no existe en los catálogos.")
        tickets = Tickets.objects.none()
        conteos = {'abiertos': 0, 'en_progreso': 0, 'cerrado': 0}

    # Paginación
    paginator = Paginator(tickets, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/admin.html', {
        'admin_user': usuario,
        'page_obj': page_obj,
        'dashboard_headers': Tickets.TICKET_ADMIN_HEADERS,
        'tickets_abiertos_count': conteos.get('abiertos', 0),
        'tickets_en_progreso_count': conteos.get('en_progreso', 0),
        'tickets_cerrado_count': conteos.get('cerrado', 0),
        'es_superadmin': False,
    })


# ==============================================================================
# 3. DASHBOARD DEL SUPERADMINISTRADOR (Global)
# ==============================================================================

@login_required
@user_passes_test(lambda u: u.es_superadmin_tipo)
def superadmin_dashboard(request):
    """
    Dashboard global. Ve todos los tickets del sistema y tiene acceso 
    a los reportes avanzados y filtros globales.
    """
    # Llama a las queries globales que definiste con Aggregate (1 sola consulta SQL)
    tickets = Tickets.objects.todos_ordenados()
    conteos = Tickets.conteos_superadmin()

    # Paginación
    paginator = Paginator(tickets, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/admin.html', { # O 'superadmin/superadmin.html' según tu estructura
        'admin_user': request.user,
        'page_obj': page_obj,
        'dashboard_headers': Tickets.TICKET_SUPERADMIN_HEADERS,
        'tickets_abiertos_count': conteos.get('abiertos', 0),
        'tickets_en_progreso_count': conteos.get('en_progreso', 0),
        'tickets_cerrado_count': conteos.get('cerrado', 0),
        'es_superadmin': True,
        # Cargamos las áreas combinadas para el modal de reportes
        'areas_reporte': Tickets.get_areas_para_reporte(), 
    })


# ==============================================================================
# 4. REPORTES Y GRÁFICOS (SuperAdmin)
# ==============================================================================

def generar_grafico_mensual(queryset):
    """Genera un gráfico de barras a partir del queryset filtrado y retorna base64."""
    if not queryset.exists():
        return None
        
    df = pd.DataFrame(list(queryset.values('fecha_creacion')))
    df['fecha'] = df['fecha_creacion'].dt.date
    counts = df['fecha'].value_counts().sort_index()

    plt.figure(figsize=(10, 5))
    counts.plot(kind='bar', color='#1abc9c')
    plt.title('Tickets Generados por Día (Últimos 30 días)', fontsize=14)
    plt.xlabel('Fecha')
    plt.ylabel('Cantidad de Tickets')
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    plt.close()
    
    return image_base64

@login_required
@user_passes_test(lambda u: u.es_superadmin_tipo)
def reporte_pdf(request):
    """
    Genera el archivo PDF interactivo usando Weasyprint y Matplotlib.
    """
    # Ejemplo: Obtener tickets de los últimos 30 días para el reporte
    hace_30_dias = timezone.now() - timedelta(days=30)
    tickets_para_grafico = Tickets.objects.filter(fecha_creacion__gte=hace_30_dias)

    grafico_mensual_b64 = generar_grafico_mensual(tickets_para_grafico)

    if not grafico_mensual_b64:
        messages.warning(request, "No hay suficientes datos para generar el gráfico.")

    # Contexto para el template HTML del PDF
    context = {
        'usuario': request.user,
        'fecha_generacion': timezone.now(),
        'grafico_mensual_b64': grafico_mensual_b64,
        'total_tickets_mes': tickets_para_grafico.count(),
        'tickets_resueltos': tickets_para_grafico.filter(estado__id_estado='cerrado').count() # Uso de la nueva ForeignKey 'estado'
    }

    html_string = render_to_string('superadmin/reporte_template.html', context)

    try:
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        result = html.write_pdf()

        response = HttpResponse(result, content_type='application/pdf')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M')
        response['Content-Disposition'] = f'attachment; filename="Reporte_Gerencial_{timestamp}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Ocurrió un error al generar el PDF: {str(e)}")
        return redirect('usuario:superadmin_dashboard')