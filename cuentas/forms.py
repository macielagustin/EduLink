from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario, Alumno, Maestro, Provincia, Departamento, Municipio, Localidad, Idioma, NivelEducativo, Disponibilidad
from catalogo.models import Materia


class RegistroPersonaForm(UserCreationForm):
    email = forms.EmailField(required=True)
    fecha_nacimiento = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}), 
        required=False
    )
    bio = forms.CharField(  # campo personalizado que mapea a descripcion
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="Descripción"
    )

    # Campos de geolocalización
    provincia = forms.ModelChoiceField(queryset=Provincia.objects.all(), required=False)
    departamento = forms.ModelChoiceField(queryset=Departamento.objects.none(), required=False)
    municipio = forms.ModelChoiceField(queryset=Municipio.objects.none(), required=False)
    localidad = forms.ModelChoiceField(queryset=Localidad.objects.none(), required=False)
    calle = forms.CharField(max_length=255, required=False)
    latitud = forms.FloatField(widget=forms.HiddenInput(), required=False)
    longitud = forms.FloatField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Usuario
        fields = (
            "username", "email", "password1", "password2",
            "telefono", "fecha_nacimiento", "foto_perfil",
            "provincia", "departamento", "municipio", "localidad",
            "calle", "latitud", "longitud"
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = "Mín. 8 caracteres y al menos una mayúscula."
        self.fields["password2"].help_text = "Repetí la misma contraseña."

        # --- selects dependientes (geolocalización) ---
        if 'provincia' in self.data:
            try:
                provincia_id = int(self.data.get('provincia'))
                self.fields['departamento'].queryset = Departamento.objects.filter(provincia_id=provincia_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.provincia:
            self.fields['departamento'].queryset = self.instance.provincia.departamento_set.all()

        if 'departamento' in self.data:
            try:
                departamento_id = int(self.data.get('departamento'))
                self.fields['municipio'].queryset = Municipio.objects.filter(departamento_id=departamento_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.departamento:
            self.fields['municipio'].queryset = self.instance.departamento.municipio_set.all()

        if 'municipio' in self.data:
            try:
                municipio_id = int(self.data.get('municipio'))
                self.fields['localidad'].queryset = Localidad.objects.filter(municipio_id=municipio_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.municipio:
            self.fields['localidad'].queryset = self.instance.municipio.localidad_set.all()

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.descripcion = self.cleaned_data.get("bio")  # mapeo bio → descripcion
        if commit:
            usuario.save()
        return usuario


class RegistroAlumnoForm(forms.ModelForm):
    materias_interes = forms.ModelMultipleChoiceField(
        queryset=Materia.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "6"})
    )
    disponibilidad = forms.ModelMultipleChoiceField(
        queryset=Disponibilidad.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "4"})
    )

    class Meta:
        model = Alumno
        fields = (
            "nivel_educativo",
            "materias_interes",
            "objetivo",
            "disponibilidad",
            "prefiere_online",
        )


class RegistroMaestroForm(forms.ModelForm):
    materias = forms.ModelMultipleChoiceField(
        queryset=Materia.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "6"})
    )
    idiomas = forms.ModelMultipleChoiceField(
        queryset=Idioma.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "4"})
    )

    class Meta:
        model = Maestro
        fields = (
            "precio_hora",
            "modalidad",   # ✅ reemplaza online/presencial
            "descripcion",
            "cv",
            "materias",
            "idiomas",
        )


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario o Email")

