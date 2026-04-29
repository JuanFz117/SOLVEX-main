from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

Usuario = get_user_model()

# Verificar si el modelo ya está registrado
if Usuario in admin.site._registry:
    admin.site.unregister(Usuario)

# Crear un filtro personalizado para 'rol' ya que no lo reconoce como campo a filtrar en el admin
class RolFilter(admin.SimpleListFilter):
    title = 'Rol'  # Título que aparecerá en el administrador
    parameter_name = 'rol'  # Nombre del parámetro en la URL

    def lookups(self, request, model_admin):
        """Opciones de filtro basadas en ROLE_CHOICES."""
        return Usuario.ROLE_CHOICES

    def queryset(self, request, queryset):
        """Filtrar el queryset según el valor seleccionado."""
        if self.value():
            return queryset.filter(rol=self.value())
        return queryset

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'rol', 'categoria')
    list_filter = (RolFilter, 'categoria','is_staff', 'is_superuser')  # Usar el filtro personalizado
    search_fields = ('username', 'email', 'first_name', 'last_name', 'id_usuario')

    ordering = ('username',)
    fieldsets = (
        (None, {'fields': ('username', 'password', 'email', 'rol', 'categoria', 'id_usuario', 'nombre', 'cargo', 'area_agencia', 'debe_cambiar_contrasena')}),
        ('Roles y Permisos', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2','email', 'rol', 'categoria', 'id_usuario', 'nombre', 'cargo', 'area_agencia', 'debe_cambiar_contrasena', 'is_staff', 'is_active'),
        }),
    )