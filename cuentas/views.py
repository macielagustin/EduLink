from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from .forms import RegistroPersonaForm, RegistroAlumnoForm, RegistroMaestroForm, LoginForm

def home_view(request):
    return render(request, "home.html")

def registro_persona(request):
    if request.method == "POST":
        form = RegistroPersonaForm(request.POST)
        if form.is_valid():
            usuario = form.save()  # guarda con contraseña hasheada
            messages.success(request, "¡Cuenta creada! Elegí tu rol para continuar.")
            login(request, usuario)  # lo logueamos para simplificar el flujo
            return redirect("elegir_rol")
    else:
        form = RegistroPersonaForm()
    return render(request, "cuentas/registro_persona.html", {"form": form})

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
            request.user.rol = "ALUMNO"
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
            request.user.rol = "MAESTRO"
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

