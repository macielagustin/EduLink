from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from .forms import RegistroPersonaForm, RegistroAlumnoForm, RegistroMaestroForm, LoginForm
from .models import Departamento, Municipio, Localidad


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
    departamentos = Departamento.objects.filter(provincia_id=provincia_id).all()
    return JsonResponse(list(departamentos.values('id', 'nombre')), safe=False)


def load_municipios(request):
    departamento_id = request.GET.get('departamento_id')
    municipios = Municipio.objects.filter(departamento_id=departamento_id).all()
    return JsonResponse(list(municipios.values('id', 'nombre')), safe=False)


def load_localidades(request):
    municipio_id = request.GET.get('municipio_id')
    localidades = Localidad.objects.filter(municipio_id=municipio_id).all()
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


@login_required
def dashboard_alumno(request):
    return render(request, "cuentas/dashboard_alumno.html")


@login_required
def dashboard_maestro(request):
    return render(request, "cuentas/dashboard_maestro.html")
