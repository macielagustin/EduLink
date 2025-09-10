from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario, Alumno, Maestro
from catalogo.models import Materia

class RegistroPersonaForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = Usuario
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mensajitos útiles
        self.fields["password1"].help_text = "Mín. 8 caracteres y al menos una mayúscula."
        self.fields["password2"].help_text = "Repetí la misma contraseña."

class RegistroAlumnoForm(forms.ModelForm):
    class Meta:
        model = Alumno
        fields = ("bio", "prefiere_online", "ciudad")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3})
        }

class RegistroMaestroForm(forms.ModelForm):
    materias = forms.ModelMultipleChoiceField(
        queryset=Materia.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "6"})
    )

    class Meta:
        model = Maestro
        fields = ("bio", "precio_hora", "online", "presencial", "ciudad", "materias", "cv")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
            "precio_hora": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario o Email")
