from django.db import models
# from usuario.models import Usuario
from datetime import datetime
from django.conf import settings

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
    
# ============= Modelo Tickets: Representa los tickets creados por los colaboradores. ============= #
class Tickets(models.Model):
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