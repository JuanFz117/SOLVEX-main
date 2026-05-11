from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError


# ================================================================
# MANAGER PERSONALIZADO PARA EL MODELO USUARIO
# ================================================================
# El manager es el encargado de crear usuarios en la base de datos.
# Se personaliza para agregar validaciones adicionales y para
# asignar valores por defecto según el tipo de usuario.
# ================================================================
class UsuarioManager(BaseUserManager):

    def create_user(self, username, id_usuario, password=None, **extra_fields):
        """
        Crea y guarda un usuario normal en la base de datos.
        Valida que el username y el id_usuario (cédula) sean correctos
        antes de guardar.
        """
        if not username:
            raise ValueError('El nombre de usuario es obligatorio')
        if not id_usuario:
            raise ValueError('El ID de usuario es obligatorio')

        # Validar que la cédula sea un número entero
        try:
            int(id_usuario)
        except ValueError:
            raise ValidationError('El ID de usuario debe ser un número entero')

        # Si no se especifica un rol, se asigna colaborador por defecto
        extra_fields.setdefault('rol', self.model.ROLE_COLABORADOR)

        user = self.model(username=username, id_usuario=id_usuario, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, id_usuario, password=None, **extra_fields):
        """
        Crea y guarda un superusuario en la base de datos.
        Un superusuario tiene acceso total al panel de administración
        de Django y al panel de SOLVEX.
        """
        # Los superusuarios siempre deben tener estos permisos activos
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('rol', self.model.ROLE_SUPERADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(username, id_usuario, password, **extra_fields)


# ================================================================
# MODELO PRINCIPAL DE USUARIO
# ================================================================
# Extiende AbstractUser de Django para agregar campos y lógica
# específica de SOLVEX como roles, categorías y propiedades
# de navegación.
# ================================================================
class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado que extiende AbstractUser.
    Centraliza toda la lógica de roles, categorías y redirecciones.
    """

    # ================================================================
    # CONSTANTES DE ROLES
    # ================================================================

    ROLE_SUPERADMIN = 'superadmin'   # Acceso total al sistema
    ROLE_ADMIN = 'admin'             # Gestiona y resuelve tickets
    ROLE_COLABORADOR = 'colaborador' # Crea y consulta sus tickets

    ROLE_CHOICES = (
        (ROLE_SUPERADMIN, 'Superadministrador'),
        (ROLE_ADMIN, 'Administrador'),
        (ROLE_COLABORADOR, 'Colaborador'),
    )

    # ================================================================
    # CONSTANTES DE CATEGORÍAS
    # ================================================================
    # La categoría define qué tipo de tickets puede ver y gestionar
    # un administrador. Un admin de "Soporte Técnico" solo ve tickets
    # de soporte técnico, y así sucesivamente.
    # ================================================================
    CAT_SOPORTE_TECNICO = 'Soporte Técnico'
    CAT_SOPORTE_OPERATIVO = 'Soporte Operativo'
    CAT_DESARROLLO = 'Área de Desarrollo'

    CATEGORIAS = [
        (CAT_SOPORTE_TECNICO, 'Soporte Técnico'),
        (CAT_SOPORTE_OPERATIVO, 'Soporte Operativo'),
        (CAT_DESARROLLO, 'Área de Desarrollo'),
    ]

    # ================================================================
    # CAMPOS DEL MODELO
    # ================================================================
    # Campos adicionales al modelo base de Django (AbstractUser).
    # AbstractUser ya provee: username, password, email, first_name,
    # last_name, is_staff, is_active, is_superuser, date_joined.
    # ================================================================

    # Número de cédula del usuario, único en el sistema
    id_usuario = models.IntegerField(
        unique=True, null=False, blank=False,
        verbose_name='ID (cédula)'
    )

    # Nombre completo del usuario (diferente a first_name de Django)
    nombre = models.CharField(max_length=255, null=False, blank=False)

    # Cargo que ocupa el usuario en la organización
    cargo = models.CharField(max_length=255, null=False, blank=False)

    # Agencia o área donde trabaja el usuario
    area_agencia = models.CharField(max_length=255, null=False, blank=False)

    # Email único por usuario, usado para envío de recordatorios via SendGrid
    email = models.EmailField(
        verbose_name='email address', max_length=255, unique=True
    )

    # Flag para forzar cambio de contraseña en el primer login
    debe_cambiar_contrasena = models.BooleanField(default=True)

    # Solo aplica para administradores, define qué tickets pueden gestionar
    categoria = models.CharField(
        max_length=255, choices=CATEGORIAS, null=True, blank=True
    )

    # Rol del usuario en el sistema (colaborador por defecto)
    rol = models.CharField(
        max_length=255, choices=ROLE_CHOICES, default=ROLE_COLABORADOR
    )

    # Usar el manager personalizado para creación de usuarios
    objects = UsuarioManager()

    USERNAME_FIELD = 'username'

    # rol y categoria NO están aquí porque tienen valores por defecto
    # y no deben pedirse al crear un superusuario por consola
    REQUIRED_FIELDS = ['nombre', 'cargo', 'id_usuario', 'email']

    def __str__(self):
        return f"{self.username} ({self.id_usuario})"

    # ================================================================
    # PROPERTIES DE ROL
    # ================================================================

    @property
    def es_admin_tipo(self):
        """
        True si el usuario es admin o superadmin.
        Usado para verificar acceso a vistas administrativas.
        """
        return self.rol in [self.ROLE_ADMIN, self.ROLE_SUPERADMIN]

    @property
    def es_superadmin_tipo(self):
        """
        True si el usuario es superadmin.
        Usado para mostrar/ocultar opciones exclusivas del superadmin
        como reportes y gestión global de tickets.
        """
        return self.rol == self.ROLE_SUPERADMIN

    @property
    def es_colaborador(self):
        """
        True si el usuario autenticado es colaborador.
        Los colaboradores solo pueden crear y consultar sus propios tickets.
        """
        return self.is_authenticated and self.rol == self.ROLE_COLABORADOR

    @property
    def es_admin_o_superadmin(self):
        """
        True si el usuario autenticado es admin o superadmin.
        Usado principalmente en decoradores @user_passes_test de las vistas.
        """
        return self.is_authenticated and self.rol in [self.ROLE_ADMIN, self.ROLE_SUPERADMIN]

    # ================================================================
    # PROPERTIES DE CATEGORÍA
    # ================================================================

    @property
    def tiene_categoria(self):
        """
        True si el admin tiene una categoría asignada.
        Un admin sin categoría no podrá ver tickets en su dashboard
        ya que los tickets se filtran por tipo_soporte = categoria.
        """
        return bool(self.categoria)

    # ================================================================
    # PROPERTIES DE NAVEGACIÓN
    # ================================================================
    # Centralizan la lógica de redirección según el rol del usuario.
    # ================================================================

    @property
    def get_dashboard_url(self):
        """
        Retorna la URL del dashboard correspondiente al rol del usuario.

        - Superadmin  → /usuario/superadmin_dashboard/
        - Admin       → /usuario/admin_dashboard/
        - Colaborador → /tickets/inicio/

        Elimina la lógica de redirección quemada en las vistas,
        centralizando en el modelo la decisión de a dónde va cada rol.
        """
        from django.urls import reverse
        if self.es_superadmin_tipo:
            return reverse('usuario:superadmin_dashboard')
        elif self.es_admin_tipo:
            return reverse('usuario:admin_dashboard')
        return reverse('tickets:index')