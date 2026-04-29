from django  import forms
from django.contrib.auth.forms import PasswordChangeForm

class CambiarContraseñaForm(PasswordChangeForm):
    """
    Formulario para cambiar la contraseña del usuario.
    """
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['old_password'].label = 'Contraseña Genérica'
        self.fields['new_password1'].label = 'Nueva Contraseña'
        self.fields['new_password2'].label = 'Confirmar Nueva Contraseña'