from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario, Alumno, Maestro, Provincia, Departamento, Municipio, Localidad, Idioma, NivelEducativo, Disponibilidad
from catalogo.models import Materia


class RegistroPersonaForm(UserCreationForm):
    email = forms.EmailField(required=True)
    nombre = forms.CharField(max_length=50, required=True, label="Nombre")
    apellido = forms.CharField(max_length=50, required=True, label="Apellido")

    fecha_nacimiento = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}), 
        required=False
    )
    bio = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="Descripción"
    )

    # Campos de geolocalización (extras, no del modelo)
    provincia = forms.CharField(
    max_length=100, required=False,
    widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    departamento = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    municipio = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    localidad = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )

    calle = forms.CharField(max_length=255, required=False)
    latitud = forms.FloatField(widget=forms.HiddenInput(), required=False)
    longitud = forms.FloatField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Usuario
        fields = (
            "username", "email", "password1", "password2",
            "nombre", "apellido", "telefono", "fecha_nacimiento", "foto_perfil",
            "calle", "latitud", "longitud"   # 👈 sacamos los FK de aquí
        )

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.descripcion = self.cleaned_data.get("bio")
        usuario.nombre = self.cleaned_data.get("nombre")
        usuario.apellido = self.cleaned_data.get("apellido")

        # Procesamos los campos manualmente
        provincia_nombre = self.cleaned_data.get("provincia")
        if provincia_nombre:
            prov_obj, _ = Provincia.objects.get_or_create(nombre=provincia_nombre)
            usuario.provincia = prov_obj

        departamento_nombre = self.cleaned_data.get("departamento")
        if departamento_nombre and usuario.provincia:
            depto_obj, _ = Departamento.objects.get_or_create(
                nombre=departamento_nombre,
                provincia=usuario.provincia
            )
            usuario.departamento = depto_obj

        municipio_nombre = self.cleaned_data.get("municipio")
        if municipio_nombre and usuario.departamento:
            muni_obj, _ = Municipio.objects.get_or_create(
                nombre=municipio_nombre,
                departamento=usuario.departamento
            )
            usuario.municipio = muni_obj

        localidad_nombre = self.cleaned_data.get("localidad")
        if localidad_nombre and usuario.municipio:
            loc_obj, _ = Localidad.objects.get_or_create(
                nombre=localidad_nombre,
                municipio=usuario.municipio
            )
            usuario.localidad = loc_obj

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

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = [
            "first_name", "last_name", "email", "telefono",
            "fecha_nacimiento", "bio", "foto_perfil"
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "foto_perfil": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

class AlumnoForm(forms.ModelForm):
    class Meta:
        model = Alumno
        fields = ["nivel_educativo", "materias_interes", "objetivo", "disponibilidad", "prefiere_online"]
        widgets = {
            "nivel_educativo": forms.Select(attrs={"class": "form-select"}),
            "materias_interes": forms.SelectMultiple(attrs={"class": "form-select"}),
            "objetivo": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "disponibilidad": forms.SelectMultiple(attrs={"class": "form-select"}),
            "prefiere_online": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }





class EditarPerfilMaestroForm(forms.ModelForm):
    # Campos del usuario que queremos editar
    first_name = forms.CharField(
        max_length=30, 
        required=True, 
        label="Nombre",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True, 
        label="Apellido",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    # Campos específicos del maestro
    precio_hora = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        label="Precio por hora ($)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    modalidad = forms.ChoiceField(
        choices=[
            ("Online", "Online"),
            ("Presencial", "Presencial"),
            ("Ambos", "Ambos"),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    descripcion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label="Descripción sobre ti"
    )
    
    cv = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label="Curriculum Vitae (PDF)"
    )
    
    materias = forms.ModelMultipleChoiceField(
        queryset=Materia.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="Materias que enseñas"
    )
    
    idiomas = forms.ModelMultipleChoiceField(
        queryset=Idioma.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="Idiomas que hablas"
    )

    class Meta:
        model = Maestro
        fields = ['precio_hora', 'modalidad', 'descripcion', 'cv', 'materias', 'idiomas']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si ya existe una instancia, cargamos los datos del usuario
        if self.instance and self.instance.usuario:
            self.fields['first_name'].initial = self.instance.usuario.first_name
            self.fields['last_name'].initial = self.instance.usuario.last_name
            self.fields['email'].initial = self.instance.usuario.email

    def save(self, commit=True):
        maestro = super().save(commit=False)
        # Actualizamos también los datos del usuario
        if commit:
            usuario = maestro.usuario
            usuario.first_name = self.cleaned_data['first_name']
            usuario.last_name = self.cleaned_data['last_name']
            usuario.email = self.cleaned_data['email']
            usuario.save()
            maestro.save()
            self.save_m2m()  # Para guardar las relaciones ManyToMany
        return maestro