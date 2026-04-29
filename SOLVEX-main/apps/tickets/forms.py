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
        agencia_corresponsal = cleaned_data.get('agencia_corresponsal')
        administrativa = cleaned_data.get('administrativa')

        if administrativa == 'No Aplica' and agencia_corresponsal == 'No Aplica':
            raise forms.ValidationError("Debe seleccionar Administrativa o Agencia/Corresponsal, no puede seleccionar ambos como no aplica")
        
        # Valid|ación: Si Agencia / Corresponsal es diferente de "No Aplica, entonces administrativa debe ser No Aplica".
        if agencia_corresponsal != 'No Aplica' and administrativa != 'No Aplica':
            raise forms.ValidationError("Si seleccionas una Agencia/Corresponsal, Administrativa debe ser 'No Aplica' (VICEVERSA).")
                
        return cleaned_data
    
class ComentarioForm(forms.ModelForm):
    """
    Formulario para crear comentarios a un ticket.
    """
    class Meta:
        model = Ticket_comentarios
        fields=[
            'detalle_comentario',
            'adjunto'
        ]
        widgets = {
            'detalle_comentario': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escribe tu comentario aquí...', 'class': 'form-control'}),
            'adjunto': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'detalle_comentario': 'Comentario',
            'adjunto': 'Adjunto (opcional)',
        }
        help_texts = {
            'detalle_comentario': 'Escribe aquí tu mensaje para el colaborador.',
        }