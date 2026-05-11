from django.db import models
from datetime import datetime
from django.conf import settings
from django.db.models import Q, Count, Case, When, IntegerField

# ==============================================================================
# 1. TABLAS MAESTRAS (Catálogos Dinámicos)
# ==============================================================================

class TipoSoporte(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Tipo de Soporte'
        verbose_name_plural = 'Tipos de Soporte'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class AgenciaCorresponsal(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Agencia / Corresponsal'
        verbose_name_plural = 'Agencias y Corresponsales'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class AreaAdministrativa(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Área Administrativa'
        verbose_name_plural = 'Áreas Administrativas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class MotivoCierre(models.Model):
    # ¡Corregido! Incluye el campo código para filtrar fácilmente en reportes
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)

    class Meta:
        verbose_name = 'Motivo de Cierre'
        verbose_name_plural = 'Motivos de Cierre'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# ==============================================================================
# 2. ESTADOS Y PRIORIDADES (Cero código quemado)
# ==============================================================================
# ¡Corregido! Ya no hay listas quemadas (ESTADOS o PRIORIDADES) aquí.

class Ticket_estado(models.Model):
    id_estado = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Estado de Ticket'
        verbose_name_plural = 'Estados de Ticket'

    def __str__(self):
        return self.nombre


class Ticket_prioridad(models.Model):
    id_prioridad = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Prioridad de Ticket'
        verbose_name_plural = 'Prioridades de Ticket'

    def __str__(self):
        return self.nombre


# ==============================================================================
# 3. GESTOR DE CONSULTAS (Manager Optimizado)
# ==============================================================================

class TicketsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related(
            'usuario', 'asignado_a',
            'tipo_soporte', 'agencia_corresponsal',
            'administrativa', 'motivo_cierre'
        )

    # --- Métodos de Colaboradores ---
    def abiertos_por_usuario(self, usuario):
        return self.get_queryset().filter(
            Q(id_estado='abierto') | Q(id_estado='en_progreso'),
            usuario=usuario
        )

    # ¡Corregido! Agregado método faltante
    def cerrados_por_usuario(self, usuario):
        return self.get_queryset().filter(usuario=usuario, id_estado='cerrado')

    # --- Métodos de Administradores ---
    def abiertos_por_categoria(self, tipo_soporte_id):
        return self.get_queryset().filter(
            Q(id_estado='abierto') | Q(id_estado='en_progreso'),
            tipo_soporte_id=tipo_soporte_id
        ).order_by('-fecha_creacion')

    # ¡Corregido! Agregado método faltante
    def cerrados_por_categoria(self, tipo_soporte_id):
        return self.get_queryset().filter(
            id_estado='cerrado',
            tipo_soporte_id=tipo_soporte_id
        )

    # --- Métodos Globales y Utilidades ---
    def todos_ordenados(self):
        return self.get_queryset().order_by('-fecha_creacion')

    # ¡Corregido! Agregado prefetch faltante
    def con_comentarios(self):
        return self.get_queryset().prefetch_related('Comentarios')


# ==============================================================================
# 4. MODELO PRINCIPAL DE TICKETS
# ==============================================================================

class Tickets(models.Model):
    objects = TicketsManager()

    # ¡Corregido! TODOS los headers incluidos
    TICKET_ABIERTO_HEADERS = ['ID', 'Motivo', 'Tipo de Soporte', 'Estado', 'Prioridad', 'Fecha de Creación']
    TICKET_CERRADO_HEADERS = ['ID', 'Motivo', 'Tipo de Soporte', 'Estado', 'Fecha de Creación', 'Fecha de Solución']
    TICKET_DETALLE_HEADERS = ['ID', 'Tipo de Soporte', 'Área Reportada', 'Estado', 'Prioridad', 'Fecha de Creación']
    TICKET_ADMIN_HEADERS = ['ID', 'Motivo', 'Usuario', 'Tipo de Soporte', 'Estado', 'Prioridad', 'Fecha de Creación']
    TICKET_ADMIN_CERRADO_HEADERS = ['ID', 'Motivo', 'Usuario', 'Tipo de Soporte', 'Estado', 'Fecha de Creación', 'Fecha de Solución']
    TICKET_SUPERADMIN_HEADERS = ['ID', 'Motivo', 'Usuario', 'Tipo de Soporte', 'Estado', 'Prioridad', 'Fecha de Creación', 'Asignado A']

    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='Tickets_creados', on_delete=models.CASCADE, null=True, blank=True)
    
    # Estados y Prioridades sin choices
    id_estado = models.CharField(max_length=20, default='abierto')
    id_prioridad = models.CharField(max_length=20, null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    asignado_a = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='Tickets_asignados', on_delete=models.CASCADE, null=True, blank=True)

    motivo = models.CharField(max_length=255)
    detalle = models.TextField()

    # ForeignKeys a tablas maestras (Mi contribución: Integridad referencial)
    tipo_soporte = models.ForeignKey(TipoSoporte, on_delete=models.PROTECT, verbose_name='Tipo de Soporte')
    agencia_corresponsal = models.ForeignKey(AgenciaCorresponsal, on_delete=models.PROTECT, verbose_name='Agencia / Corresponsal')
    administrativa = models.ForeignKey(AreaAdministrativa, on_delete=models.PROTECT, verbose_name='Área Administrativa')
    motivo_cierre = models.ForeignKey(MotivoCierre, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Motivo de Cierre')

    adjuntos = models.FileField(upload_to='tickets/', blank=True, null=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'

    def __str__(self):
        return f'Ticket {self.id} - {self.usuario.username if self.usuario else "Sistema"}'

    # --- Lógica de Negocio (Fat Model) ---
    
    def asignar_ticket(self, admin_user):
        self.fecha_asignacion = datetime.now()
        self.id_estado = 'en_progreso'
        self.asignado_a = admin_user
        self.save()

    def cerrar_ticket(self, motivo_obj):
        self.fecha_cierre = datetime.now()
        self.id_estado = 'cerrado'
        self.motivo_cierre = motivo_obj
        self.save()

    def get_estado_display(self):
        try:
            return Ticket_estado.objects.get(id_estado=self.id_estado).nombre
        except Ticket_estado.DoesNotExist:
            return self.id_estado

    def get_prioridad_display(self):
        if not self.id_prioridad: return '—'
        try:
            return Ticket_prioridad.objects.get(id_prioridad=self.id_prioridad).nombre
        except Ticket_prioridad.DoesNotExist:
            return self.id_prioridad

    def preparar_datos_para_websocket(self):
        from django.urls import reverse
        return {
            'id': self.id,
            'motivo': self.motivo,
            'usuario_username': self.usuario.username if self.usuario else 'Sistema',
            'tipo_soporte': self.tipo_soporte.nombre,
            'estado_display': self.get_estado_display(),
            'fecha_creacion': self.fecha_creacion.isoformat(),
        }

    # --- MÉTODOS DE CLASE PARA REPORTES Y DASHBOARDS ---

    @classmethod
    def conteos_por_categoria(cls, tipo_soporte_id):
        return cls.objects.filter(tipo_soporte_id=tipo_soporte_id).aggregate(
            abiertos=Count(Case(When(id_estado='abierto', then=1), output_field=IntegerField())),
            en_progreso=Count(Case(When(id_estado='en_progreso', then=1), output_field=IntegerField())),
            cerrado=Count(Case(When(id_estado='cerrado', then=1), output_field=IntegerField())),
        )

    @classmethod
    def conteos_superadmin(cls):
        return cls.objects.aggregate(
            abiertos=Count(Case(When(id_estado='abierto', then=1), output_field=IntegerField())),
            en_progreso=Count(Case(When(id_estado='en_progreso', then=1), output_field=IntegerField())),
            cerrado=Count(Case(When(id_estado='cerrado', then=1), output_field=IntegerField())),
        )

    @classmethod
    def get_areas_para_reporte(cls):
        agencias = (
            AgenciaCorresponsal.objects
            .filter(activo=True)
            .exclude(nombre__iexact='No Aplica')
            .values_list('nombre', flat=True)
        )
        areas = (
            AreaAdministrativa.objects
            .filter(activo=True)
            .exclude(nombre__iexact='No Aplica')
            .values_list('nombre', flat=True)
        )
        return sorted(set(list(agencias) + list(areas)))

    @classmethod
    def get_opciones_soporte(cls):
        return {
            'Tipo_de_Soporte': TipoSoporte.objects.all(),
            'Agencia_Corresponsal': AgenciaCorresponsal.objects.filter(activo=True),
            'Administrativa': AreaAdministrativa.objects.filter(activo=True),
            'Prioridades': Ticket_prioridad.objects.all(),
        }


# ==============================================================================
# 5. HISTORIAL DE COMENTARIOS
# ==============================================================================

class Ticket_comentarios(models.Model):
    id_comment = models.AutoField(primary_key=True)
    id_ticket = models.ForeignKey(Tickets, on_delete=models.CASCADE, related_name='Comentarios')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='Comentarios_realizados')
    hora_comentario = models.DateTimeField(auto_now_add=True)
    detalle_comentario = models.TextField()
    adjunto = models.FileField(upload_to='comentarios/', blank=True, null=True)

    def __str__(self):
        user_display = self.autor.username if self.autor else 'Sistema'
        return f'Comentario {self.id_comment} en Ticket {self.id_ticket.id} por {user_display}'

    @classmethod
    def crear_comentario(cls, ticket, autor, detalle_comentario, adjunto=None):
        return cls.objects.create(
            id_ticket=ticket, 
            autor=autor, 
            detalle_comentario=detalle_comentario, 
            adjunto=adjunto
        )

    def puede_ser_editado_por(self, usuario):
        return self.autor == usuario