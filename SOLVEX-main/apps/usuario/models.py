from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError

class UsuarioManager(BaseUserManager):
    def create_user(self, username, id_usuario, password=None, **extra_fields):
        if not username:
            raise ValueError('El nombre de usuario es obligatorio')
        if not id_usuario:
            raise ValueError('El ID de usuario es obligatorio')
        
        try:
            int(id_usuario)
        except ValueError:
            raise ValidationError('El ID de usuario debe ser un número entero')
        
        extra_fields.setdefault('rol', 'colaborador')
        user = self.model(username=username, id_usuario=id_usuario,**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, id_usuario, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('rol', 'superadmin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')   
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')
        
        # Llama la funcion pasando el id_usuario como argumento
        return self.create_user(username, id_usuario, password, **extra_fields)
        
class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado que extiende AbstractUser y agrega un campo de rol.
    """

    ROLE_CHOICES = (
        ('superadmin', 'Superadministrador'),
        ('admin', 'Administrador'),
        ('colaborador', 'Colaborador'),
    )
    CATEGORIAS = [
        ('Soporte Técnico', 'Soporte Técnico'),
        ('Soporte Operativo', 'Soporte Operativo'),
        ('Área de Desarrollo', 'Área de Desarrollo'),
    ]

    id_usuario = models.IntegerField(unique=True, null=False, blank=False, verbose_name= 'ID (cédula)')  # ID único para cada usuario.
    nombre = models.CharField(max_length=255, null=False, blank=False)  # Nombre del usuario.
    cargo = models.CharField(max_length=255, null=False, blank=False)  # Cargo del usuario.
    area_agencia = models.CharField(max_length=255, null=False, blank=False)  # Área o agencia del usuario.
    email = models.EmailField(verbose_name='email address', max_length=255, unique=True)  # Email del usuario.
    debe_cambiar_contrasena = models.BooleanField(default=True)  # Indica si el usuario debe cambiar su contraseña.
    # username = models.CharField(max_length=150, unique=True) # VOY A UTILIZAR EL USERNAME DEL MODELO PADRE
    categoria = models.CharField(max_length=255, choices=CATEGORIAS ,null=True, blank=True)  # Categoría del usuario.
    rol = models.CharField(max_length=20, choices=ROLE_CHOICES, default='colaborador')  # Rol del usuario.

    objects = UsuarioManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['nombre', 'cargo', 'id_usuario', 'email']  # Campos obligatorios al crear un superusuario]

    def __str__(self):
        return f"{self.username} ({self.id_usuario})"  # Representación legible del usuario.