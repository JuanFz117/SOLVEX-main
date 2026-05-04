from django.db import models
# from usuario.models import Usuario
from datetime import datetime
from django.conf import settings
from django.db.models import Q

# ============= Modelo Ticket_estado: Define los estados posibles de un ticket. ============ #
class Ticket_estado(models.Model):
    ESTADOS = [
        ('abierto', 'Abierto'),
        ('en_progreso', 'En Progreso'),
        ('cerrado', 'Cerrado'),
    ]
    id_estado = models.CharField(max_length=20, choices=ESTADOS, primary_key=True) # ID único para cada estado.
    
    def __str__(self):
        return self.get_id_estado_display()  # Devuelve la representación legible del estado.

# ============== Modelo Ticket_prioridad: Define las prioridades posibles de un ticket. ============= #
class Ticket_prioridad(models.Model):
    PRIORIDADES = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
    ]
    id_prioridad = models.CharField(max_length=20, choices=PRIORIDADES, primary_key=True) # ID único para cada prioridad.
    
    def __str__(self):
        return self.get_id_prioridad_display()  # Devuelve la representación legible de la prioridad.
    
# ============= Manager personalizado para Tickets ============= #
class TicketsManager(models.Manager):
    """Manager personalizado para optimizar consultas de tickets."""
    
    def get_queryset(self):
        return super().get_queryset().select_related('usuario', 'asignado_a')
    
    def abiertos_por_usuario(self, usuario):
        """Obtiene tickets abiertos o en progreso de un usuario."""
        return self.get_queryset().filter(
            Q(id_estado="abierto") | Q(id_estado="en_progreso"),
            usuario=usuario
        )
    
    def cerrados_por_usuario(self, usuario):
        """Obtiene tickets cerrados de un usuario."""
        return self.get_queryset().filter(usuario=usuario, id_estado="cerrado")
    
    def con_comentarios(self):
        """Prefetch comentarios para evitar N+1 queries."""
        return self.get_queryset().prefetch_related('Comentarios')
    
# ============= Modelo Tickets: Representa los tickets creados por los colaboradores. ============= #
class Tickets(models.Model):
    objects = TicketsManager()
    TIPO_DE_SOPORTE = [
        ('Soporte Técnico', 'Soporte Técnico'),
        ('Soporte Operativo', 'Soporte Operativo'),
        ('Área de Desarrollo', 'Área de Desarrollo'),
    ]

    MOTIVO_CIERRE_CHOICES = [
        ('resuelto', 'Resuelto'),
        ('error_aplicativo', 'Error de aplicativo'),
        ('error_usuario', 'Error de usuario'),
        ('falta_capacitacion', 'Falta de capacitación'),
        ('duplicado', 'Ticket duplicado'),
        ('no_corresponde', 'No corresponde a esta área'),
    ]

    # Constants for hardcoded values in views
    AGENCIA_CORRESPONSAL_CHOICES = [
        ('No Aplica', 'No Aplica'),
        ('Agencia Principal', 'Agencia Principal'),
        ('Agencia Popular', 'Agencia Popular'),
        ('Agencia Catama', 'Agencia Catama'),
        ('Agencia Porfía', 'Agencia Porfía'),
        ('Agencia Montecarlo', 'Agencia Montecarlo'),
        ('Agencia Acacías', 'Agencia Acacías'),
        ('Agencia Vistahermosa', 'Agencia Vistahermosa'),
        ('Agencia Guayabetal', 'Agencia Guayabetal'),
        ('Agencia Barranca de Upía', 'Agencia Barranca de Upía'),
        ('Agencia Cabuyaro', 'Agencia Cabuyaro'),
        ('Agencia Puerto Gaitán', 'Agencia Puerto Gaitán'),
        ('Corresponsal Puerto López', 'Corresponsal Puerto López'),
        ('Corresponsal El Castillo', 'Corresponsal El Castillo'),
        ('Corresponsal Lejanías', 'Corresponsal Lejanías'),
        ('Corresponsal Puerto Lleras', 'Corresponsal Puerto Lleras'),
        ('Corresponsal Puerto Rico', 'Corresponsal Puerto Rico'),
        ('Corresponsal Cumaral', 'Corresponsal Cumaral'),
        ('Corresponsal Mesetas', 'Corresponsal Mesetas'),
        ('Corresponsal Uribe', 'Corresponsal Uribe'),
        ('Corresponsal Yopal', 'Corresponsal Yopal'),
        ('Corresponsal Villanueva', 'Corresponsal Villanueva')
    ]

    ADMINISTRATIVA_CHOICES = [
        ('No Aplica', 'No Aplica'),
        ('Gerencia General', 'Gerencia General'),
        ('Gerencia Innovación y Transformación', 'Gerencia Innovación y Transformación'),
        ('Gerencia Comercial', 'Gerencia Comercial'),
        ('Oficial de Cumplimiento', 'Oficina de Cumplimiento'),
        ('Oficial de Riesgo', 'Oficial de Riesgo'),
        ('Servicios Administrativos', 'Servicios Administrativos'),
        ('Talento Humano', 'Talento Humano'),
        ('Operaciones', 'Operaciones'),
        ('Contabilidad', 'Contabilidad'),
        ('Revisoría', 'Revisoría'),
        ('Auditoria', 'Auditoria'),
        ('Credito', 'Credito'),
        ('Cartera', 'Cartera'),
        ('Cobranza', 'Cobranza'),
        ('Garantías', 'Garantías'),
        ('Comunicaciones', 'Comunicaciones'),
        ('Convenios', 'Convenios'),
        ('Canales', 'Canales'),
    ]

    # Table headers constants
    TICKET_ABIERTO_HEADERS = ['ID', 'Motivo', 'Tipo de Soporte', 'Estado', 'Prioridad', 'Fecha de Creación']
    TICKET_CERRADO_HEADERS = ['ID', 'Motivo', 'Tipo de Soporte', 'Estado', 'Fecha de Creación', 'Fecha de Solución']
    TICKET_DETALLE_HEADERS = ['ID', 'Tipo de Soporte', 'Area reportada', 'Estado', 'Prioridad', 'Fecha de Creación']

    id = models.AutoField(primary_key=True)  # ID único para cada ticket.
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='Tickets_creados', on_delete=models.CASCADE, null=True, blank=True)  # Relación con el colaborador que crea el ticket.
    id_estado = models.CharField(max_length=20, choices=Ticket_estado.ESTADOS, default="abierto")  # Estado del ticket, predeterminado a "abierto".
    id_prioridad = models.CharField(max_length=20, choices=Ticket_prioridad.PRIORIDADES, null=True, blank=True)  # Prioridad del ticket.
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # Fecha de creación automática.
    fecha_asignacion = models.DateTimeField(null=True, blank=True)  # Fecha de asignación (se llena cuando el ticket se asigna).
    fecha_cierre = models.DateTimeField(null=True, blank=True)  # Fecha de cierre (se llena cuando el ticket se cierra).
    motivo_cierre = models.CharField(max_length=255, choices=MOTIVO_CIERRE_CHOICES, null=True, blank=True)  # Motivo de cierre (cuando cierre el caso).
    asignado_a = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='Tickets_asignados', on_delete=models.CASCADE, null=True, blank=True)  # Colaborador asignado al ticket.
    motivo = models.CharField(max_length=255, null=False, blank=False) # Motivo del soporte
    tipo_soporte = models.CharField(max_length=255, null=False, blank=False)  # Tipo de soporte (técnico u operativo).
    agencia_corresponsal = models.CharField(max_length=255, null=False, blank=False)  # Agencia o corresponsal asociado.
    administrativa = models.CharField(max_length=255, null=False, blank=False)  # Área administrativa.
    detalle = models.TextField(blank=False, null=False)  # Detalle del ticket.
    adjuntos = models.FileField(upload_to='', blank=True, null=True)  # Archivos adjuntos (opcionales).

    def __str__(self):
        return f'Ticket {self.id} - {self.usuario.username  if self.usuario else "Sin asignar"}'  # Representación legible del ticket.

    class Meta:
        ordering = ['-fecha_creacion']  # Ordenar tickets por fecha de creacion mas reciente.
        verbose_name = 'Ticket'  # Nombre singular en el admin.
        verbose_name_plural = 'Tickets'  # Nombre plural en el admin.

    # Métodos para cambiar el estado del ticket.
    def asignar_ticket(self):
        """Marca el ticket como 'En Progreso' y registra la fecha de asignación."""
        self.fecha_asignacion = datetime.now()
        self.id_estado = 'en_progreso'
        self.save()

    def cerrar_ticket(self):
        """Cierra el ticket y registra la fecha de cierre."""
        self.fecha_cierre = datetime.now()
        self.id_estado = 'cerrado'
        self.save()

    def preparar_datos_para_websocket(self):
        """
        Prepara los datos del ticket para enviar vía WebSocket.
        """
        from django.urls import reverse
        return {
            'id': self.id,
            'motivo': self.motivo,
            'usuario_username': self.usuario.username,
            'tipo_soporte': self.tipo_soporte,
            'estado_display': self.get_id_estado_display(),
            'estado_value': self.id_estado,
            'prioridad_display': self.get_id_prioridad_display(),
            'prioridad_value': self.id_prioridad,
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'url_detalle_admin': reverse('tickets:admin_ticket_detail', kwargs={'ticket_id': self.id})
        }

    # Métodos para obtener opciones de formularios
    @classmethod
    def get_opciones_soporte(cls):
        """
        Obtiene las opciones de soporte para los formularios.
        """
        return {
            'Tipo_de_Soporte': {
                'Soporte Técnico': 'Soporte Técnico',
                'Soporte Operativo': 'Soporte Operativo',
                'Área de Desarrollo': 'Área de Desarrollo'
            },
            'Agencia_Corresponsal': dict(cls.AGENCIA_CORRESPONSAL_CHOICES),
            'Administrativa': dict(cls.ADMINISTRATIVA_CHOICES),
            'Prioridades': dict(Ticket_prioridad.PRIORIDADES),
        }

# ========== Modelo Ticket_comentarios: Representa los comentarios asociados a un ticket. ========== #
class Ticket_comentarios(models.Model):
    id_comment = models.AutoField(primary_key=True)  # ID único para cada comentario.
    id_ticket = models.ForeignKey(Tickets, on_delete=models.CASCADE, related_name='Comentarios')  # Relación con el ticket.
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name= 'Comentarios_realizados')  # Relación con el colaborador que hizo el comentario.
    hora_comentario = models.DateTimeField(auto_now_add=True)  # Fecha y hora del comentario.
    detalle_comentario = models.TextField(blank=False, null=False)  # Contenido del comentario.
    adjunto = models.FileField(upload_to='comentarios/', blank=True, null=True)  # Archivos adjuntos al comentario (opcionales).

    def __str__(self):
        user_display = self.autor.username if self.autor else "Sistema"
        return f"Comentario {self.id_comment} en Ticket {self.id_ticket.id} por {user_display}"

    @classmethod
    def crear_comentario(cls, ticket, autor, detalle_comentario, adjunto=None):
        """
        Crea un nuevo comentario para un ticket.
        """
        return cls.objects.create(
            id_ticket=ticket,
            autor=autor,
            detalle_comentario=detalle_comentario,
            adjunto=adjunto
        )

    def puede_ser_editado_por(self, usuario):
        """
        Verifica si un usuario puede editar este comentario.
        Por ahora, solo el autor puede editar.
        """
        return self.autor == usuario