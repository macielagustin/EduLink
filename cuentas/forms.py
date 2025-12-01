from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario, Alumno, Maestro, Provincia, Departamento, Municipio, Localidad, Idioma, NivelEducativo, Disponibilidad, SolicitudClase, Mensaje, Reseña, DisponibilidadUsuario, ReseñaAlumno, BlocNotas, Tarea, SesionEstudio, Institucion, Promocion, Voucher, Nota
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

    institucion = forms.ModelChoiceField(
    queryset=Institucion.objects.filter(activa=True),
    required=False,
    widget=forms.Select(attrs={'class': 'form-select'}),
    label="Institución/Escuela"
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
    cbu_cvu_alias = forms.CharField(
        max_length=100,
        required=False,
        label="CBU/CVU o Alias",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Para recibir pagos por transferencia'})
    )

    class Meta:
        model = Maestro
        fields = (
            "precio_hora",
            "modalidad",
            "descripcion",
            "cv",
            "materias",
            "idiomas",
            "cbu_cvu_alias",  # Nuevo campo
        )


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario o Email")

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = [
            "nombre", "apellido", "email", "telefono",
            "fecha_nacimiento", "bio", "foto_perfil"
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "apellido": forms.TextInput(attrs={"class": "form-control"}),
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
    nombre = forms.CharField(
        max_length=30, 
        required=True, 
        label="Nombre",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    apellido = forms.CharField(
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
    foto_perfil = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label="Foto de perfil"
    )
    eliminar_foto = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Eliminar foto actual"
    )

    # Campos de ubicación
    provincia = forms.ModelChoiceField(
        queryset=Provincia.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_provincia'})
    )
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_departamento'})
    )
    municipio = forms.ModelChoiceField(
        queryset=Municipio.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_municipio'})
    )
    localidad = forms.ModelChoiceField(
        queryset=Localidad.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_localidad'})
    )
    calle = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_calle'})
    )
    latitud = forms.FloatField(
        widget=forms.HiddenInput(attrs={'id': 'id_latitud'}),
        required=False
    )
    longitud = forms.FloatField(
        widget=forms.HiddenInput(attrs={'id': 'id_longitud'}),
        required=False
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

    # ✅ Campo nuevo correctamente declarado
    cbu_cvu_alias = forms.CharField(
        required=False,
        max_length=50,
        label="CBU / CVU / Alias",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: ALIAS.MP o número de CBU'
        })
    )

    class Meta:
        model = Maestro
        fields = [
            'precio_hora', 'modalidad', 'descripcion', 'cv',
            'materias', 'idiomas', 'cbu_cvu_alias'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Resto de tu inicialización (queda igual)...
        if self.instance and self.instance.usuario:
            usuario = self.instance.usuario
            self.fields['nombre'].initial = usuario.nombre
            self.fields['apellido'].initial = usuario.apellido
            self.fields['email'].initial = usuario.email
            self.fields['foto_perfil'].initial = usuario.foto_perfil
            self.fields['provincia'].initial = usuario.provincia
            self.fields['departamento'].initial = usuario.departamento
            self.fields['municipio'].initial = usuario.municipio
            self.fields['localidad'].initial = usuario.localidad
            self.fields['calle'].initial = usuario.calle
            self.fields['latitud'].initial = usuario.latitud
            self.fields['longitud'].initial = usuario.longitud

            if usuario.provincia:
                self.fields['departamento'].queryset = Departamento.objects.filter(provincia=usuario.provincia)
            if usuario.departamento:
                self.fields['municipio'].queryset = Municipio.objects.filter(departamento=usuario.departamento)
            if usuario.municipio:
                self.fields['localidad'].queryset = Localidad.objects.filter(municipio=usuario.municipio)

    def save(self, commit=True):
        maestro = super().save(commit=False)
        if commit:
            usuario = maestro.usuario
            usuario.nombre = self.cleaned_data['nombre']
            usuario.apellido = self.cleaned_data['apellido']
            usuario.email = self.cleaned_data['email']

            if self.cleaned_data.get('eliminar_foto') and usuario.foto_perfil:
                usuario.foto_perfil.delete(save=False)
                usuario.foto_perfil = None
            elif self.cleaned_data.get('foto_perfil'):
                usuario.foto_perfil = self.cleaned_data['foto_perfil']

            usuario.provincia = self.cleaned_data['provincia']
            usuario.departamento = self.cleaned_data['departamento']
            usuario.municipio = self.cleaned_data['municipio']
            usuario.localidad = self.cleaned_data['localidad']
            usuario.calle = self.cleaned_data['calle']
            usuario.latitud = self.cleaned_data['latitud']
            usuario.longitud = self.cleaned_data['longitud']

            usuario.save()
            maestro.save()
            self.save_m2m()
        return maestro

    


class SolicitudClaseForm(forms.ModelForm):
    class Meta:
        model = SolicitudClase
        fields = ['materia', 'duracion_minutos', 'mensaje']
        widgets = {
            'duracion_minutos': forms.NumberInput(attrs={'class': 'form-control', 'min': '30', 'step': '30'}),
            'mensaje': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Explica qué necesitas aprender...'}),
            'materia': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        # Extraemos el maestro pasado desde la vista
        maestro = kwargs.pop('maestro', None)
        super().__init__(*args, **kwargs)

        # Valor inicial de duración
        self.fields['duracion_minutos'].initial = 60

        # Si hay maestro, filtramos las materias que enseña
        if maestro:
            self.fields['materia'].queryset = maestro.materias.all()


class MensajeForm(forms.ModelForm):
    archivo = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control d-none',
            'id': 'archivo-input',
            'accept': '.pdf,.doc,.docx,.txt,.zip,.rar,.7z'
        })
    )
    
    imagen = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control d-none',
            'id': 'imagen-input',
            'accept': 'image/*'
        })
    )

    class Meta:
        model = Mensaje
        fields = ['contenido', 'archivo', 'imagen']
        widgets = {
            'contenido': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Escribe tu mensaje...',
                'id': 'mensaje-contenido'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        contenido = cleaned_data.get('contenido')
        archivo = cleaned_data.get('archivo')
        imagen = cleaned_data.get('imagen')
        
        # Validar que al menos haya contenido o un archivo
        if not contenido and not archivo and not imagen:
            raise forms.ValidationError('Debes escribir un mensaje o adjuntar un archivo/imagen.')
        
        # Validar tamaño máximo de archivos (10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if archivo and archivo.size > max_size:
            raise forms.ValidationError(f'El archivo es demasiado grande. Máximo: 10MB.')
        if imagen and imagen.size > max_size:
            raise forms.ValidationError(f'La imagen es demasiado grande. Máximo: 10MB.')
        
        return cleaned_data


"""

class ResenaForm(forms.ModelForm):
    class Meta:
        model = Resena
        fields = ['calificacion', 'comentario']
        widgets = {
            'calificacion': forms.RadioSelect(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
            'comentario': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Comparte tu experiencia...'}),
        } """



class ProponerFechaForm(forms.ModelForm):
    class Meta:
        model = SolicitudClase
        fields = ['fecha_clase_propuesta', 'monto_acordado', 'metodo_pago']
        widgets = {
            'fecha_clase_propuesta': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'monto_acordado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agregar formato aceptado para datetime-local
        self.fields['fecha_clase_propuesta'].input_formats = ['%Y-%m-%dT%H:%M']

        # Si ya hay una fecha cargada, convertirla al formato HTML5 correcto
        if self.instance and self.instance.fecha_clase_propuesta:
            self.initial['fecha_clase_propuesta'] = self.instance.fecha_clase_propuesta.strftime('%Y-%m-%dT%H:%M')




# Formulario para que el alumno confirme la fecha
class ConfirmarFechaForm(forms.ModelForm):
    class Meta:
        model = SolicitudClase
        fields = ['fecha_clase_confirmada', 'metodo_pago']  # Agregar metodo_pago
        widgets = {
            'fecha_clase_confirmada': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
        }




# Formulario para disponibilidad
class DisponibilidadForm(forms.ModelForm):
    class Meta:
        model = DisponibilidadUsuario
        fields = ['titulo', 'fecha_inicio', 'fecha_fin', 'tipo', 'descripcion']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'fecha_fin': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }




# Agregar este formulario después de los existentes
class MetodoPagoForm(forms.ModelForm):
    class Meta:
        model = SolicitudClase
        fields = ['metodo_pago']
        widgets = {
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
        }
""" 
class ConfirmarFechaForm(forms.ModelForm):
    class Meta:
        model = SolicitudClase
        fields = ['fecha_clase_confirmada', 'metodo_pago']  # Agregar metodo_pago
        widgets = {
            'fecha_clase_confirmada': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
        } """

class ReseñaForm(forms.ModelForm):
    class Meta:
        model = Reseña
        fields = ['puntuacion', 'comentario']
        widgets = {
            'puntuacion': forms.HiddenInput(),  # lo manejamos con JavaScript (estrellas clickeables)
            'comentario': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Escribí un comentario (opcional)...',
                'class': 'form-control'
            }),
        }




class ReseñaAlumnoForm(forms.ModelForm):
    class Meta:
        model = ReseñaAlumno
        fields = ['puntuacion', 'comentario']
        widgets = {
            'puntuacion': forms.HiddenInput(),
            'comentario': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Comentario sobre el alumno (opcional)...',
                'class': 'form-control',
            }),
        }

# ===== HERRAMIENTAS INTEGRADAS =====
class BlocNotasForm(forms.ModelForm):
    class Meta:
        model = BlocNotas
        fields = []  # No hay campos editables


class TareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = ['titulo', 'descripcion', 'fecha_vencimiento', 'prioridad']  # Quitamos 'estado'
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Título de la tarea...',
                'required': 'required'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Descripción de la tarea...'
            }),
            'fecha_vencimiento': forms.DateTimeInput(attrs={
                'type': 'datetime-local', 
                'class': 'form-control'
            }),
            'prioridad': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer que solo el título sea obligatorio
        self.fields['titulo'].required = True
        self.fields['prioridad'].required = True

class SesionEstudioForm(forms.ModelForm):
    class Meta:
        model = SesionEstudio
        fields = ['tipo', 'descripcion']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '¿Qué vas a estudiar?'}),
        }



class InstitucionForm(forms.ModelForm):
    class Meta:
        model = Institucion
        fields = ['nombre', 'direccion', 'telefono', 'email']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class PromocionForm(forms.ModelForm):
    class Meta:
        model = Promocion
        fields = ['nombre', 'tipo', 'valor', 'descripcion', 'fecha_inicio', 'fecha_fin', 'max_usos']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'fecha_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'fecha_fin': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'max_usos': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class VoucherForm(forms.ModelForm):
    class Meta:
        model = Voucher
        fields = ['codigo', 'promocion', 'alumno', 'maestro']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'promocion': forms.Select(attrs={'class': 'form-select'}),
            'alumno': forms.Select(attrs={'class': 'form-select'}),
            'maestro': forms.Select(attrs={'class': 'form-select'}),
        }

class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = ['titulo', 'contenido']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título de la nota...'
            }),
            'contenido': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'placeholder': 'Escribe tu nota aquí... Puedes usar markdown básico.'
            }),
        }

# Modificar el RegistroPersonaForm para incluir institución
# Agregar este campo al formulario existente:
# institucion = forms.ModelChoiceField(
#     queryset=Institucion.objects.filter(activa=True),
#     required=False,
#     widget=forms.Select(attrs={'class': 'form-select'}),
#     label="Institución/Escuela"
# )

