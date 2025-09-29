from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from .forms import RegistroPersonaForm, RegistroAlumnoForm, RegistroMaestroForm, LoginForm, UsuarioForm, AlumnoForm
from .models import Departamento, Municipio, Localidad, Provincia, Maestro, Alumno
from catalogo.models import Materia
import math

from .forms import EditarPerfilMaestroForm  # Asegúrate de importar el formulario
from .models import SolicitudClase
from django.db.models import Q  # Para búsquedas complejas


def home_view(request):
    return render(request, "home.html")


def registro_persona(request):
    if request.method == "POST":
        form = RegistroPersonaForm(request.POST, request.FILES)  # acepta archivos (foto_perfil)
        if form.is_valid():
            usuario = form.save()  # guarda con contraseña hasheada

            raw_password = form.cleaned_data.get("password1") or form.cleaned_data.get("password")
            user_auth = None

            # Intento autenticación por username
            if getattr(usuario, "username", None):
                user_auth = authenticate(request, username=usuario.username, password=raw_password)

            # Intento autenticación por email
            if user_auth is None and getattr(usuario, "email", None):
                user_auth = authenticate(request, email=usuario.email, password=raw_password)

            # Logueo
            if user_auth is not None:
                login(request, user_auth)
            else:
                login(request, usuario, backend=settings.AUTHENTICATION_BACKENDS[0])

            messages.success(request, "¡Cuenta creada! Elegí tu rol para continuar.")
            return redirect("elegir_rol")
    else:
        form = RegistroPersonaForm()
    return render(request, "cuentas/registro_persona.html", {"form": form})


# --- Vistas AJAX para selects dependientes ---
def load_departamentos(request):
    provincia_id = request.GET.get('provincia_id')
    departamentos = Departamento.objects.filter(provincia_id=provincia_id)
    return JsonResponse(list(departamentos.values('id', 'nombre')), safe=False)


def load_municipios(request):
    departamento_id = request.GET.get('departamento_id')
    municipios = Municipio.objects.filter(departamento_id=departamento_id)
    return JsonResponse(list(municipios.values('id', 'nombre')), safe=False)


def load_localidades(request):
    municipio_id = request.GET.get('municipio_id')
    localidades = Localidad.objects.filter(municipio_id=municipio_id)
    return JsonResponse(list(localidades.values('id', 'nombre')), safe=False)


@login_required
def elegir_rol(request):
    return render(request, "cuentas/elegir_rol.html")


@login_required
def registro_alumno(request):
    if request.method == "POST":
        form = RegistroAlumnoForm(request.POST)
        if form.is_valid():
            perfil = form.save(commit=False)
            perfil.usuario = request.user
            perfil.save()
            request.user.rol = "ALUMNO"  # mantenemos tu nomenclatura
            request.user.save(update_fields=["rol"])
            messages.success(request, "¡Registro como Alumno completado!")
            return redirect("dashboard_alumno")
    else:
        form = RegistroAlumnoForm()
    return render(request, "cuentas/registro_alumno.html", {"form": form})


@login_required
def registro_maestro(request):
    if request.method == "POST":
        form = RegistroMaestroForm(request.POST, request.FILES)
        if form.is_valid():
            perfil = form.save(commit=False)
            perfil.usuario = request.user
            perfil.save()
            form.save_m2m()
            request.user.rol = "MAESTRO"  # mantenemos tu nomenclatura
            request.user.save(update_fields=["rol"])
            messages.success(request, "¡Registro como Maestro completado!")
            return redirect("dashboard_maestro")
    else:
        form = RegistroMaestroForm()
    return render(request, "cuentas/registro_maestro.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "cuentas/login.html"
    authentication_form = LoginForm

    def get_success_url(self):
        u = self.request.user
        if u.rol == "MAESTRO":
            return "/maestro/"
        if u.rol == "ALUMNO":
            return "/alumno/"
        return "/"


def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada.")
    return redirect("login")

#######################################
######### ALUMNO #####################
######################################

@login_required
def dashboard_alumno(request):
    return render(request, "cuentas/dashboard_alumno.html")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radio de la Tierra en km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@login_required
def buscar_clases(request):
    materias = Materia.objects.all()
    provincias = Provincia.objects.all()

    # Capturar parámetros de búsqueda
    materia_id = request.GET.get("materia")
    modalidad = request.GET.get("modalidad")
    provincia_id = request.GET.get("provincia")
    radio = request.GET.get("radio")
    vista = request.GET.get("view", "list")  # 👈 list o map

    # Convertir a enteros los IDs
    if materia_id:
        try:
            materia_id = int(materia_id)
        except ValueError:
            materia_id = None

    if provincia_id:
        try:
            provincia_id = int(provincia_id)
        except ValueError:
            provincia_id = None

    resultados = Maestro.objects.all()

    # Filtros básicos
    if materia_id:
        resultados = resultados.filter(materias__id=materia_id)
    if modalidad:
        resultados = resultados.filter(modalidad=modalidad)
    if provincia_id:
        resultados = resultados.filter(usuario__provincia__id=provincia_id)

    # Filtro por radio solo si es presencial
    resultados_finales = []
    if modalidad == "Presencial" and radio:
        alumno = request.user
        if alumno.latitud and alumno.longitud:
            radio = float(radio)
            for m in resultados:
                if m.usuario.latitud and m.usuario.longitud:
                    distancia = haversine(
                        alumno.latitud, alumno.longitud,
                        m.usuario.latitud, m.usuario.longitud
                    )
                    if distancia <= radio:
                        resultados_finales.append((m, round(distancia, 1)))
    else:
        # Si no aplica filtro de radio → devolvemos todos con distancia = None
        resultados_finales = [(m, None) for m in resultados]

    context = {
        "materias": materias,
        "provincias": provincias,
        "q": {
            "materia": materia_id,
            "modalidad": modalidad or "",
            "provincia": provincia_id,
            "radio": radio or "",
        },
        "resultados": resultados_finales,  # siempre lista de tuplas
        "vista": vista,  # 👈 pasamos si es lista o mapa
    }
    return render(request, "alumno/buscar_clases.html", context)



@login_required
def detalle_maestro(request, maestro_id):
    maestro = get_object_or_404(Maestro, id=maestro_id)
    usuario = maestro.usuario
    return render(request, "alumno/detalle_maestro.html", {"maestro": maestro, "usuario": usuario})

def perfil_alumno(request):
    alumno = get_object_or_404(Alumno, usuario=request.user)

    if request.method == "POST":
        usuario_form = UsuarioForm(request.POST, request.FILES, instance=request.user)
        alumno_form = AlumnoForm(request.POST, instance=alumno)

        if usuario_form.is_valid() and alumno_form.is_valid():
            usuario_form.save()
            alumno_form.save()
            return redirect("dashboard_alumno")
    else:
        usuario_form = UsuarioForm(instance=request.user)
        alumno_form = AlumnoForm(instance=alumno)

    return render(
        request,
        "alumno/perfil_alumno.html",
        {"usuario_form": usuario_form, "alumno_form": alumno_form},
    )

@login_required
def perfil_publico(request):
    alumno = get_object_or_404(Alumno, usuario=request.user)
    return render(request, "alumno/perfil_publico.html", {"alumno": alumno})

@login_required
def dashboard_maestro(request):
    return render(request, "cuentas/dashboard_maestro.html")

def test_geocoding(request):
    return render(request, "cuentas/test_geocoding.html")



"""/////////////////// MAESTRO //////////////////////"""

@login_required
def editar_perfil_maestro(request):
    try:
        # Obtenemos el perfil de maestro del usuario actual
        perfil_maestro = Maestro.objects.get(usuario=request.user)
    except Maestro.DoesNotExist:
        messages.error(request, "No tienes un perfil de maestro.")
        return redirect("dashboard_maestro")

    if request.method == "POST":
        form = EditarPerfilMaestroForm(request.POST, request.FILES, instance=perfil_maestro)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Perfil actualizado correctamente!")
            return redirect("dashboard_maestro")
    else:
        form = EditarPerfilMaestroForm(instance=perfil_maestro)

    return render(request, "maestro/editar_perfil_maestro.html", {"form": form})



@login_required
def solicitudes_para_maestro(request):
    try:
        # Obtenemos el perfil de maestro del usuario actual
        perfil_maestro = Maestro.objects.get(usuario=request.user)
        
        # Filtramos las solicitudes para este maestro
        solicitudes = SolicitudClase.objects.filter(maestro=perfil_maestro).order_by('-fecha_solicitud')
        
        # Filtros por estado
        estado_filtro = request.GET.get('estado', 'todas')
        if estado_filtro != 'todas':
            solicitudes = solicitudes.filter(estado=estado_filtro)
        
        # Contadores para los badges
        contadores = {
            'todas': SolicitudClase.objects.filter(maestro=perfil_maestro).count(),
            'pendientes': SolicitudClase.objects.filter(maestro=perfil_maestro, estado='pendiente').count(),
            'aceptadas': SolicitudClase.objects.filter(maestro=perfil_maestro, estado='aceptada').count(),
            'rechazadas': SolicitudClase.objects.filter(maestro=perfil_maestro, estado='rechazada').count(),
        }
        
    except Maestro.DoesNotExist:
        messages.error(request, "No tienes un perfil de maestro.")
        return redirect("dashboard_maestro")
    
    return render(request, "maestro/solicitudes_para_maestro.html", {
        "solicitudes": solicitudes,
        "contadores": contadores,
        "estado_filtro": estado_filtro
    })

# Vista para cambiar el estado de una solicitud
@login_required
def cambiar_estado_solicitud(request, solicitud_id, nuevo_estado):
    try:
        perfil_maestro = Maestro.objects.get(usuario=request.user)
        solicitud = SolicitudClase.objects.get(id=solicitud_id, maestro=perfil_maestro)
        
        if nuevo_estado in ['aceptada', 'rechazada']:
            solicitud.estado = nuevo_estado
            solicitud.save()
            messages.success(request, f"Solicitud {nuevo_estado} correctamente.")
        else:
            messages.error(request, "Estado no válido.")
            
    except SolicitudClase.DoesNotExist:
        messages.error(request, "Solicitud no encontrada.")
    except Maestro.DoesNotExist:
        messages.error(request, "No tienes permiso para esta acción.")
    
    return redirect("solicitudes_para_maestro")



@login_required
def agenda_maestro(request):
    try:
        perfil_maestro = Maestro.objects.get(usuario=request.user)
        
        # Obtener las clases aceptadas (futuras y pasadas)
        clases_aceptadas = SolicitudClase.objects.filter(
            maestro=perfil_maestro, 
            estado='aceptada'
        ).order_by('fecha_clase_propuesta')
        
        # Separar en próximas y pasadas
        from django.utils import timezone
        ahora = timezone.now()
        
        proximas_clases = clases_aceptadas.filter(fecha_clase_propuesta__gte=ahora)
        clases_pasadas = clases_aceptadas.filter(fecha_clase_propuesta__lt=ahora)
        
    except Maestro.DoesNotExist:
        messages.error(request, "No tienes un perfil de maestro.")
        return redirect("dashboard_maestro")
    
    return render(request, "maestro/agenda_maestro.html", {
        "proximas_clases": proximas_clases,
        "clases_pasadas": clases_pasadas,
    })



@login_required
def perfil_publico_maestro(request):
    try:
        perfil_maestro = Maestro.objects.get(usuario=request.user)
    except Maestro.DoesNotExist:
        messages.error(request, "No tienes un perfil de maestro.")
        return redirect("dashboard_maestro")
    
    return render(request, "maestro/perfil_publico_maestro.html", {
        "maestro": perfil_maestro,
        "usuario": request.user
    })

# También necesitamos una vista pública para que otros usuarios vean el perfil
def perfil_maestro_publico(request, maestro_id):
    maestro = get_object_or_404(Maestro, id=maestro_id)
    return render(request, "maestro/perfil_maestro_publico.html", {
        "maestro": maestro,
        "usuario_maestro": maestro.usuario
    })

