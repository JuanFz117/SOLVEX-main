from django import forms
from .models import Tickets, Ticket_comentarios

class TicketsForm(forms.ModelForm):
    """
    Formulario para crear tickets.
    """
    class Meta:
        model = Tickets
        fields = [
            'tipo_soporte',
            'agencia_corresponsal',
            'administrativa',
            'id_prioridad',
            'motivo', 
            'detalle',
            'adjuntos',
        ]
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Obtenemos las instancias (objetos) de la base de datos
        agencia = cleaned_data.get('agencia_corresponsal')
        admin = cleaned_data.get('administrativa')

        # Extraemos el texto del nombre para poder compararlo con 'No Aplica'
        nombre_agencia = agencia.nombre if agencia else ''
        nombre_admin = admin.nombre if admin else ''

        # Validación 1: No pueden ser ambos "No Aplica"
        if nombre_admin == 'No Aplica' and nombre_agencia == 'No Aplica':
            raise forms.ValidationError("Debe seleccionar Administrativa o Agencia/Corresponsal, no puede seleccionar ambos como 'No Aplica'.")
        
        # Validación 2: Si selecciona una agencia, administrativa debe ser "No Aplica" (y viceversa)
        if nombre_agencia != 'No Aplica' and nombre_admin != 'No Aplica':
            raise forms.ValidationError("Si seleccionas una Agencia/Corresponsal, Administrativa debe ser 'No Aplica' (VICEVERSA).")
                
        return cleaned_data
    

class ComentarioForm(forms.ModelForm):
    """
    Formulario para crear comentarios a un ticket.
    """
    class Meta:
        model = Ticket_comentarios
        fields = [
            'detalle_comentario',
            'adjunto'
        ]
        widgets = {
            'detalle_comentario': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Escribe tu comentario aquí...', 
                'class': 'form-control'
            }),
            'adjunto': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            })
        }
        labels = {
            'detalle_comentario': 'Comentario',
            'adjunto': 'Adjunto (opcional)',
        }
        help_texts = {
            'detalle_comentario': 'Escribe aquí tu mensaje para el colaborador.',
        }