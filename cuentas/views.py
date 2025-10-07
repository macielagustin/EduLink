from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from .forms import RegistroPersonaForm, RegistroAlumnoForm, RegistroMaestroForm, LoginForm, UsuarioForm, AlumnoForm, ConfirmarFechaForm, DisponibilidadForm
from .models import Departamento, Municipio, Localidad, Provincia, Maestro, Alumno, Usuario, DisponibilidadUsuario
from catalogo.models import Materia
import math

from .utils import enviar_email
from django.contrib.auth.forms import PasswordResetForm

from .forms import EditarPerfilMaestroForm  # Asegúrate de importar el formulario
from .models import SolicitudClase
from django.db.models import Q  # Para búsquedas complejas
from django.utils import timezone
from .models import Conversacion, Mensaje
from .forms import SolicitudClaseForm, MensajeForm, ProponerFechaForm

from django.http import JsonResponse
from django.db.models import Count, Avg, Q, Sum
from .models import Notificacion, Resena
from .forms import ResenaForm
import json
from datetime import datetime, timedelta



# Agregar estas funciones utilitarias al inicio de views.py
def crear_notificacion(usuario, tipo, mensaje, enlace=''):
    Notificacion.objects.create(
        usuario=usuario,
        tipo=tipo,
        mensaje=mensaje,
        enlace=enlace
    )

def verificar_disponibilidad_maestro(maestro, fecha_propuesta, duracion_minutos):
    """Verifica si el maestro tiene disponibilidad en la fecha propuesta"""
    fecha_fin = fecha_propuesta + timedelta(minutes=duracion_minutos)
    
    # Buscar clases aceptadas que se solapen con el horario propuesto
    clases_conflictivas = SolicitudClase.objects.filter(
        maestro=maestro,
        estado='aceptada',
        fecha_clase_propuesta__lt=fecha_fin,
        fecha_clase_propuesta__gte=fecha_propuesta - timedelta(hours=2)  # Buffer de 2 horas
    ).exists()
    
    return not clases_conflictivas


@login_required
def enviar_solicitud_clase(request, maestro_id):
    maestro = get_object_or_404(Maestro, id=maestro_id)
    alumno = get_object_or_404(Alumno, usuario=request.user)
    
    if request.method == 'POST':
        form = SolicitudClaseForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.alumno = alumno
            solicitud.maestro = maestro

            # Verificar disponibilidad del maestro
            if not verificar_disponibilidad_maestro(maestro, solicitud.fecha_clase_propuesta, solicitud.duracion_minutos):
                return JsonResponse({
                    'success': False,
                    'message': 'El maestro no está disponible en ese horario. Por favor, elige otra fecha u hora.'
                })
            
            solicitud.estado = 'pendiente'
            solicitud.save()

            # Crear notificación interna
            crear_notificacion(
                usuario=maestro.usuario,
                tipo='solicitud',
                mensaje=f'Tienes una nueva solicitud de clase de {alumno.usuario.get_full_name()}',
                enlace=f'/maestro/solicitudes/'
            )

            # ✅ Enviar correo al maestro
            mensaje_texto_maestro = (
                f"Hola {maestro.usuario.first_name or maestro.usuario.username},\n\n"
                f"El alumno {alumno.usuario.get_full_name() or alumno.usuario.username} ha solicitado una clase contigo.\n"
                "Ingresá a tu panel de EduLink para aceptar o rechazar la solicitud.\n\n"
                "Equipo de EduLink 💙"
            )

            mensaje_html_maestro = f"""
            <html>
              <body style="font-family:'Segoe UI',Roboto,sans-serif;background-color:#eaf2ff;margin:0;padding:0;">
                <div style="max-width:600px;margin:30px auto;background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
                  <div style="background:linear-gradient(180deg,#eaf2ff 0%,#fff 60%);padding:25px;text-align:center;">
                    <h2 style="color:#0d47a1;margin:0;">📩 Nueva solicitud de clase</h2>
                  </div>
                  <div style="padding:30px;color:#333;">
                    <p>Hola <strong>{maestro.usuario.first_name or maestro.usuario.username}</strong>,</p>
                    <p>El alumno <strong>{alumno.usuario.get_full_name() or alumno.usuario.username}</strong> ha solicitado una clase contigo.</p>
                    <p>Ingresá a tu panel para revisar los detalles y responder.</p>
                    <div style="text-align:center;margin:30px 0;">
                      <a href="http://127.0.0.1:8000/dashboard_maestro"
                         style="background-color:#0d6efd;color:#fff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:600;">
                        Ver solicitud
                      </a>
                    </div>
                    <p style="color:#6b7280;">— El equipo de EduLink</p>
                  </div>
                </div>
              </body>
            </html>
            """

            enviar_email(
                destinatario=maestro.usuario.email,
                asunto="📩 Nueva solicitud de clase en EduLink",
                mensaje_texto=mensaje_texto_maestro,
                mensaje_html=mensaje_html_maestro,
            )

            # ✅ Enviar correo al alumno
            mensaje_texto_alumno = (
                f"Hola {alumno.usuario.first_name or alumno.usuario.username},\n\n"
                f"Tu solicitud de clase al maestro {maestro.usuario.get_full_name() or maestro.usuario.username} fue enviada correctamente.\n"
                "Recibirás una notificación cuando el maestro acepte o rechace la clase.\n\n"
                "Equipo de EduLink 💙"
            )

            mensaje_html_alumno = f"""
            <html>
              <body style="font-family:'Segoe UI',Roboto,sans-serif;background-color:#eaf2ff;margin:0;padding:0;">
                <div style="max-width:600px;margin:30px auto;background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
                  <div style="background:linear-gradient(180deg,#eaf2ff 0%,#fff 60%);padding:25px;text-align:center;">
                    <h2 style="color:#0d47a1;margin:0;">✅ Solicitud enviada correctamente</h2>
                  </div>
                  <div style="padding:30px;color:#333;">
                    <p>Hola <strong>{alumno.usuario.first_name or alumno.usuario.username}</strong>,</p>
                    <p>Tu solicitud de clase al maestro <strong>{maestro.usuario.get_full_name() or maestro.usuario.username}</strong> fue enviada correctamente.</p>
                    <p>Recibirás un correo cuando el maestro acepte o rechace la clase.</p>
                    <div style="text-align:center;margin:30px 0;">
                      <a href="http://127.0.0.1:8000/dashboard_alumno"
                         style="background-color:#0d6efd;color:#fff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:600;">
                        Ir a mi panel
                      </a>
                    </div>
                    <p style="color:#6b7280;">— El equipo de EduLink</p>
                  </div>
                </div>
              </body>
            </html>
            """

            enviar_email(
                destinatario=alumno.usuario.email,
                asunto="✅ Tu solicitud fue enviada correctamente",
                mensaje_texto=mensaje_texto_alumno,
                mensaje_html=mensaje_html_alumno,
            )

            return JsonResponse({
                'success': True,
                'message': '¡Solicitud enviada correctamente!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Por favor, corrige los errores en el formulario.'
            })
    else:
        form = SolicitudClaseForm()
    
    return render(request, 'alumno/enviar_solicitud.html', {
        'form': form,
        'maestro': maestro
    })


# Vista para obtener notificaciones
@login_required
def obtener_notificaciones(request):
    notificaciones = Notificacion.objects.filter(
        usuario=request.user, 
        leida=False
    ).order_by('-fecha_creacion')[:10]
    
    data = [{
        'id': n.id,
        'tipo': n.tipo,
        'mensaje': n.mensaje,
        'enlace': n.enlace,
        'fecha_creacion': n.fecha_creacion.strftime("%d/%m/%Y %H:%M"),
    } for n in notificaciones]
    
    return JsonResponse(data, safe=False)

# Vista para marcar notificación como leída
@login_required
def marcar_notificacion_leida(request, notificacion_id):
    try:
        notificacion = Notificacion.objects.get(id=notificacion_id, usuario=request.user)
        notificacion.leida = True
        notificacion.save()
        return JsonResponse({'success': True})
    except Notificacion.DoesNotExist:
        return JsonResponse({'success': False})

# Vista para calendario del maestro
@login_required
def calendario_maestro(request):
    try:
        perfil_maestro = Maestro.objects.get(usuario=request.user)
        
        # Obtener clases aceptadas para el calendario
        clases = SolicitudClase.objects.filter(
            maestro=perfil_maestro,
            estado='aceptada'
        )
        
        eventos = []
        for clase in clases:
            eventos.append({
                'title': f'Clase: {clase.materia.nombre} con {clase.alumno.usuario.get_full_name()}',
                'start': clase.fecha_clase_propuesta.isoformat(),
                'end': (clase.fecha_clase_propuesta + timedelta(minutes=clase.duracion_minutos)).isoformat(),
                'color': '#28a745',
                'textColor': 'white',
                'url': f'/maestro/solicitudes/'
            })
        
    except Maestro.DoesNotExist:
        messages.error(request, "No tienes un perfil de maestro.")
        return redirect("dashboard_maestro")
    
    return render(request, "maestro/calendario_maestro.html", {
        "eventos": json.dumps(eventos)
    })

# Vista para agregar reseña
@login_required
def agregar_resena(request, clase_id):
    clase = get_object_or_404(SolicitudClase, id=clase_id)
    
    # Verificar que el usuario puede reseñar esta clase
    if request.user.rol == 'ALUMNO' and clase.alumno.usuario != request.user:
        messages.error(request, "No puedes reseñar esta clase.")
        return redirect('mis_solicitudes_alumno')
    
    if request.user.rol == 'MAESTRO' and clase.maestro.usuario != request.user:
        messages.error(request, "No puedes reseñar esta clase.")
        return redirect('solicitudes_para_maestro')
    
    # Determinar el destinatario de la reseña
    if request.user.rol == 'ALUMNO':
        destinatario = clase.maestro.usuario
    else:
        destinatario = clase.alumno.usuario
    
    if request.method == 'POST':
        form = ResenaForm(request.POST)
        if form.is_valid():
            resena = form.save(commit=False)
            resena.clase = clase
            resena.autor = request.user
            resena.destinatario = destinatario
            resena.save()
            
            messages.success(request, "¡Reseña publicada correctamente!")
            
            if request.user.rol == 'ALUMNO':
                return redirect('mis_solicitudes_alumno')
            else:
                return redirect('solicitudes_para_maestro')
    else:
        form = ResenaForm()
    
    return render(request, 'resenas/agregar_resena.html', {
        'form': form,
        'clase': clase,
        'destinatario': destinatario
    })

# Vista para ver reseñas de un usuario
def ver_resenas_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    resenas = Resena.objects.filter(destinatario=usuario).order_by('-fecha_creacion')
    
    # Calcular promedio
    promedio = resenas.aggregate(Avg('calificacion'))['calificacion__avg'] or 0
    
    return render(request, 'resenas/ver_resenas.html', {
        'usuario': usuario,
        'resenas': resenas,
        'promedio': round(promedio, 1),
        'total_resenas': resenas.count()
    })




""" ####################   COMO ANTES   ###########3# """
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
            request.user.rol = "ALUMNO"
            request.user.save(update_fields=["rol"])

            # Correo de bienvenida
            mensaje_texto = (
                f"Hola {request.user.first_name or request.user.username},\n\n"
                "Tu registro como alumno se completó exitosamente.\n"
                "Ya podés acceder a tu panel, buscar maestros y solicitar clases.\n\n"
                "Equipo de EduLink 💙"
            )

            mensaje_html = f"""
            <html>
              <body style="font-family: 'Segoe UI', Roboto, sans-serif; background-color: #eaf2ff; margin: 0; padding: 0;">
                <div style="max-width: 600px; margin: 30px auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e5e7eb; overflow: hidden;">
                  
                  <div style="background: linear-gradient(180deg, #eaf2ff 0%, #ffffff 60%); padding: 25px; text-align: center;">
                    <h2 style="color: #0d47a1; margin: 0;">¡Bienvenido a EduLink!</h2>
                    <p style="color: #6b7280; margin-top: 5px;">Tu conexión al aprendizaje personalizado 🎓</p>
                  </div>

                  <div style="padding: 30px; color: #333;">
                    <p>Hola <strong>{request.user.first_name or request.user.username}</strong>,</p>
                    <p>Tu registro como <strong>alumno</strong> se completó exitosamente ✅</p>
                    <p>Ahora podés acceder a tu panel, buscar maestros y solicitar clases personalizadas.</p>

                    <div style="text-align: center; margin: 30px 0;">
                      <a href="https://edulink.com/dashboard_alumno" 
                         style="background-color: #0d6efd; color: #fff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600;">
                        Ir al Panel
                      </a>
                    </div>

                    <p style="color: #6b7280;">Gracias por ser parte de nuestra comunidad educativa 💙</p>
                    <p style="color: #0d47a1; font-weight: 600;">— El equipo de EduLink</p>
                  </div>

                  <div style="border-top: 1px solid #e5e7eb; background: #f2f6ff; text-align: center; padding: 10px; color: #6b7280; font-size: 0.9rem;">
                    © 2025 EduLink | Plataforma de clases particulares
                  </div>
                </div>
              </body>
            </html>
            """

            from .utils import enviar_email
            enviar_email(
                destinatario=request.user.email,
                asunto="🎓 Bienvenido a EduLink",
                mensaje_texto=mensaje_texto,
                mensaje_html=mensaje_html,
            )

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

            # Versión texto (por compatibilidad)
            mensaje_texto = (
                f"Hola {request.user.first_name or request.user.username},\n\n"
                "Tu registro como maestro se completó exitosamente.\n"
                "Ya podés acceder a tu panel y comenzar a recibir solicitudes de alumnos.\n\n"
                "Equipo de EduLink 💙"
            )

            # Versión HTML (estilo EduLink)
            mensaje_html = f"""
            <html>
              <body style="font-family: 'Segoe UI', Roboto, sans-serif; background-color: #eaf2ff; margin: 0; padding: 0;">
                <div style="max-width: 600px; margin: 30px auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e5e7eb; overflow: hidden;">
                  
                  <!-- Encabezado -->
                  <div style="background: linear-gradient(180deg, #eaf2ff 0%, #ffffff 60%); padding: 25px; text-align: center;">
                    <h2 style="color: #0d47a1; margin: 0;">¡Bienvenido a EduLink!</h2>
                    <p style="color: #6b7280; margin-top: 5px;">Tu conexión al aprendizaje personalizado 🎓</p>
                  </div>

                  <!-- Cuerpo -->
                  <div style="padding: 30px; color: #333;">
                    <p>Hola <strong>{request.user.first_name or request.user.username}</strong>,</p>
                    <p>Tu registro como <strong>maestro</strong> se completó exitosamente 👨‍🏫</p>
                    <p>Ya podés acceder a tu panel y comenzar a recibir solicitudes de alumnos interesados en tus clases.</p>

                    <div style="text-align: center; margin: 30px 0;">
                      <a href="http://127.0.0.1:8000/dashboard_maestro"
                         style="background-color: #0d6efd; color: #fff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600;">
                        Ir al Panel
                      </a>
                    </div>

                    <p style="color: #6b7280;">Gracias por unirte a nuestra comunidad educativa 💙</p>
                    <p style="color: #0d47a1; font-weight: 600;">— El equipo de EduLink</p>
                  </div>

                  <!-- Pie -->
                  <div style="border-top: 1px solid #e5e7eb; background: #f2f6ff; text-align: center; padding: 10px; color: #6b7280; font-size: 0.9rem;">
                    © 2025 EduLink | Plataforma de clases particulares
                  </div>
                </div>
              </body>
            </html>
            """

            # Enviar correo
            enviar_email(
                destinatario=request.user.email,
                asunto="🎓 Bienvenido a EduLink",
                mensaje_texto=mensaje_texto,
                mensaje_html=mensaje_html,
            )

            messages.success(request, "¡Registro como Maestro completado!")
            return redirect("dashboard_maestro")

    else:
        form = RegistroMaestroForm()

    return render(request, "cuentas/registro_maestro.html", {"form": form})


#RECUPERAR CONTRASEÑA MAIL

def custom_password_reset(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name='registration/password_reset_email.html',
                html_email_template_name='registration/password_reset_email.html',
                subject_template_name='registration/password_reset_subject.txt',
            )
            messages.success(request, "Te enviamos un correo para restablecer tu contraseña.")
            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()
    return render(request, "registration/password_reset_form.html", {"form": form})

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

from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import SolicitudClase, Conversacion, Mensaje  # ajusta el import según tu app

@login_required
def dashboard_alumno(request):
    usuario = request.user
    alumno = usuario.alumno  # suponiendo que Usuario tiene relación OneToOne con Alumno

    ahora = timezone.now()

    # Solicitudes pendientes
    solicitudes_pendientes = SolicitudClase.objects.filter(
        alumno=alumno,
        estado="pendiente"
    ).count()

    # Clases esta semana (aceptadas con fecha en los próximos 7 días)
    fin_semana = ahora + timezone.timedelta(days=7)
    clases_esta_semana = SolicitudClase.objects.filter(
        alumno=alumno,
        estado="aceptada",
        fecha_clase_propuesta__gte=ahora,
        fecha_clase_propuesta__lte=fin_semana
    ).count()

    # Materias activas (materias distintas con clases aceptadas)
    materias_activas = SolicitudClase.objects.filter(
        alumno=alumno,
        estado="aceptada"
    ).values("materia").distinct().count()

    # Próximas clases (las 5 más cercanas, aceptadas)
    proximas_clases = SolicitudClase.objects.filter(
        alumno=alumno,
        estado="aceptada",
        fecha_clase_propuesta__gte=ahora
    ).order_by("fecha_clase_propuesta")[:5]

    # Conversaciones y mensajes recientes
    conversaciones = Conversacion.objects.filter(alumno=alumno).prefetch_related("mensajes")
    mensajes_recientes = []
    mensajes_nuevos = 0
    for conv in conversaciones:
        ultimo = conv.mensajes.order_by("-fecha_envio").first()
        if ultimo:
            if not ultimo.leido and ultimo.remitente != usuario:
                mensajes_nuevos += 1
            mensajes_recientes.append((conv, ultimo))

    context = {
        "solicitudes_pendientes": solicitudes_pendientes,
        "clases_esta_semana": clases_esta_semana,
        "materias_activas": materias_activas,
        "proximas_clases": proximas_clases,
        "mensajes_recientes": mensajes_recientes,
        "mensajes_nuevos": mensajes_nuevos,
    }
    return render(request, "cuentas/dashboard_alumno.html", context)


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
    modalidad = request.GET.get("modalidad", "").strip()
    provincia_id = request.GET.get("provincia")
    radio = request.GET.get("radio")
    vista = request.GET.get("view", "list")  # 👈 list o map

    # Normalizar valores
    try:
        materia_id = int(materia_id) if materia_id else None
    except ValueError:
        materia_id = None

    try:
        provincia_id = int(provincia_id) if provincia_id else None
    except ValueError:
        provincia_id = None

    try:
        radio = float(str(radio).replace(",", ".")) if radio else None
    except ValueError:
        radio = None

    resultados = Maestro.objects.all()

    # Filtros básicos
    if materia_id:
        resultados = resultados.filter(materias__id=materia_id)
    if modalidad:
        resultados = resultados.filter(modalidad=modalidad)
    if provincia_id:
        resultados = resultados.filter(usuario__provincia__id=provincia_id)

    # Filtro por radio (solo presencial)
    alumno = request.user
    resultados_finales = []

    if modalidad == "Presencial" and radio:
        if alumno.latitud and alumno.longitud:
            for m in resultados:
                if m.usuario.latitud and m.usuario.longitud:
                    distancia = haversine(
                        alumno.latitud, alumno.longitud,
                        m.usuario.latitud, m.usuario.longitud
                    )
                    if distancia <= radio:
                        resultados_finales.append((m, round(distancia, 1)))
        else:
            # Alumno sin ubicación → no aplicar filtro de radio
            resultados_finales = [(m, None) for m in resultados]
    else:
        # Si no aplica filtro de radio → devolvemos todos con distancia = None
        resultados_finales = [(m, None) for m in resultados]

    context = {
        "materias": materias,
        "provincias": provincias,
        "q": {
            "materia": materia_id or "",
            "modalidad": modalidad,
            "provincia": provincia_id or "",
            "radio": radio or "",
        },
        "resultados": resultados_finales,
        "vista": vista,
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
    try:
        perfil_maestro = Maestro.objects.get(usuario=request.user)
    except Maestro.DoesNotExist:
        messages.error(request, "No tienes un perfil de maestro.")
        return redirect("home")

    ahora = timezone.now()
    fin_semana = ahora + timezone.timedelta(days=7)

    # Datos reales
    solicitudes_pendientes = SolicitudClase.objects.filter(
        maestro=perfil_maestro,
        estado="pendiente"
    ).count()

    clases_esta_semana = SolicitudClase.objects.filter(
        maestro=perfil_maestro,
        estado="aceptada",
        fecha_clase_propuesta__gte=ahora,
        fecha_clase_propuesta__lte=fin_semana
    ).count()

    # Clases hoy
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    hoy_fin = hoy_inicio + timedelta(days=1)
    clases_hoy = SolicitudClase.objects.filter(
        maestro=perfil_maestro,
        estado="aceptada",
        fecha_clase_propuesta__gte=hoy_inicio,
        fecha_clase_propuesta__lte=hoy_fin
    ).count()

    # Ingresos del mes reales
    mes_actual = ahora.month
    año_actual = ahora.year
    ingresos_mes = SolicitudClase.objects.filter(
        maestro=perfil_maestro,
        estado="aceptada",
        fecha_clase_propuesta__month=mes_actual,
        fecha_clase_propuesta__year=año_actual
    ).aggregate(Sum('monto_acordado'))['monto_acordado__sum'] or 0

    # Próximas clases (5 más cercanas)
    proximas_clases = SolicitudClase.objects.filter(
        maestro=perfil_maestro,
        estado="aceptada",
        fecha_clase_propuesta__gte=ahora
    ).order_by('fecha_clase_propuesta')[:5]

    # Mensajes recientes
    conversaciones = Conversacion.objects.filter(maestro=perfil_maestro).prefetch_related("mensajes")
    mensajes_recientes = []
    mensajes_nuevos = 0
    
    for conv in conversaciones:
        ultimo = conv.mensajes.order_by("-fecha_envio").first()
        if ultimo:
            if not ultimo.leido and ultimo.remitente != request.user:
                mensajes_nuevos += 1
            mensajes_recientes.append((conv, ultimo))

    # Notificaciones no leídas
    notificaciones_no_leidas = Notificacion.objects.filter(
        usuario=request.user,
        leida=False
    ).count()

    context = {
        "solicitudes_pendientes": solicitudes_pendientes,
        "clases_esta_semana": clases_esta_semana,
        "clases_hoy": clases_hoy,
        "ingresos_mes": ingresos_mes,
        "proximas_clases": proximas_clases,
        "mensajes_recientes": mensajes_recientes,
        "mensajes_nuevos": mensajes_nuevos,
        "notificaciones_no_leidas": notificaciones_no_leidas,
    }
    return render(request, "cuentas/dashboard_maestro.html", context)

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

@login_required
def cambiar_estado_solicitud(request, solicitud_id, nuevo_estado):
    try:
        perfil_maestro = Maestro.objects.get(usuario=request.user)
        solicitud = SolicitudClase.objects.get(id=solicitud_id, maestro=perfil_maestro)

        if nuevo_estado in ['aceptada', 'rechazada']:
            solicitud.estado = nuevo_estado
            solicitud.save()
            messages.success(request, f"Solicitud {nuevo_estado} correctamente.")

            alumno = solicitud.alumno
            maestro = solicitud.maestro

            # 🧩 Si la solicitud fue aceptada
            if nuevo_estado == 'aceptada':
                asunto_alumno = "✅ Tu clase fue aceptada | EduLink"
                texto_alumno = (
                    f"Hola {alumno.usuario.first_name or alumno.usuario.username},\n\n"
                    f"El maestro {maestro.usuario.get_full_name() or maestro.usuario.username} aceptó tu solicitud de clase.\n\n"
                    "Podés ingresar a tu panel para coordinar los detalles.\n\n"
                    "Equipo de EduLink 💙"
                )
                html_alumno = f"""
                <html>
                  <body style="font-family:'Segoe UI',Roboto,sans-serif;background-color:#eaf2ff;margin:0;padding:0;">
                    <div style="max-width:600px;margin:30px auto;background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
                      <div style="background:linear-gradient(180deg,#eaf2ff 0%,#fff 60%);padding:25px;text-align:center;">
                        <h2 style="color:#0d47a1;margin:0;">✅ ¡Tu clase fue aceptada!</h2>
                      </div>
                      <div style="padding:30px;color:#333;">
                        <p>Hola <strong>{alumno.usuario.first_name or alumno.usuario.username}</strong>,</p>
                        <p>El maestro <strong>{maestro.usuario.get_full_name() or maestro.usuario.username}</strong> aceptó tu solicitud de clase.</p>
                        <p>Podés ingresar a tu panel para coordinar los detalles.</p>
                        <div style="text-align:center;margin:30px 0;">
                          <a href="http://127.0.0.1:8000/dashboard_alumno"
                             style="background-color:#0d6efd;color:#fff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:600;">
                            Ir a mi panel
                          </a>
                        </div>
                        <p style="color:#6b7280;">— El equipo de EduLink</p>
                      </div>
                    </div>
                  </body>
                </html>
                """

                enviar_email(
                    destinatario=alumno.usuario.email,
                    asunto=asunto_alumno,
                    mensaje_texto=texto_alumno,
                    mensaje_html=html_alumno,
                )

            # 🧩 Si la solicitud fue rechazada
            elif nuevo_estado == 'rechazada':
                asunto_alumno = "❌ Tu solicitud fue rechazada | EduLink"
                texto_alumno = (
                    f"Hola {alumno.usuario.first_name or alumno.usuario.username},\n\n"
                    f"El maestro {maestro.usuario.get_full_name() or maestro.usuario.username} rechazó tu solicitud de clase.\n\n"
                    "Podés solicitar otra fecha o elegir otro maestro desde tu panel.\n\n"
                    "Equipo de EduLink 💙"
                )
                html_alumno = f"""
                <html>
                  <body style="font-family:'Segoe UI',Roboto,sans-serif;background-color:#eaf2ff;margin:0;padding:0;">
                    <div style="max-width:600px;margin:30px auto;background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
                      <div style="background:linear-gradient(180deg,#eaf2ff 0%,#fff 60%);padding:25px;text-align:center;">
                        <h2 style="color:#0d47a1;margin:0;">❌ Solicitud rechazada</h2>
                      </div>
                      <div style="padding:30px;color:#333;">
                        <p>Hola <strong>{alumno.usuario.first_name or alumno.usuario.username}</strong>,</p>
                        <p>El maestro <strong>{maestro.usuario.get_full_name() or maestro.usuario.username}</strong> rechazó tu solicitud de clase.</p>
                        <p>Podés solicitar otra clase o elegir otro maestro desde tu panel.</p>
                        <div style="text-align:center;margin:30px 0;">
                          <a href="http://127.0.0.1:8000/dashboard_alumno"
                             style="background-color:#0d6efd;color:#fff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:600;">
                            Volver a mi panel
                          </a>
                        </div>
                        <p style="color:#6b7280;">— El equipo de EduLink</p>
                      </div>
                    </div>
                  </body>
                </html>
                """

                enviar_email(
                    destinatario=alumno.usuario.email,
                    asunto=asunto_alumno,
                    mensaje_texto=texto_alumno,
                    mensaje_html=html_alumno,
                )

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
        
        # Estadísticas adicionales
        solicitudes_pendientes = SolicitudClase.objects.filter(
            maestro=perfil_maestro, 
            estado='pendiente'
        ).count()
        
        # Calcular ingresos del mes (simplificado)
        ingresos_mes = clases_aceptadas.filter(
            fecha_clase_propuesta__month=ahora.month,
            fecha_clase_propuesta__year=ahora.year
        ).aggregate(Sum('monto_acordado'))['monto_acordado__sum'] or 0
        
    except Maestro.DoesNotExist:
        messages.error(request, "No tienes un perfil de maestro.")
        return redirect("dashboard_maestro")
    
    return render(request, "maestro/agenda_maestro.html", {
        "proximas_clases": proximas_clases,
        "clases_pasadas": clases_pasadas,
        "solicitudes_pendientes": solicitudes_pendientes,
        "ingresos_mes": ingresos_mes,
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




# VISTAS PARA ALUMNO - SOLICITUDES

@login_required
def enviar_solicitud_clase(request, maestro_id):
    maestro = get_object_or_404(Maestro, id=maestro_id)
    alumno = get_object_or_404(Alumno, usuario=request.user)
    
    if request.method == 'POST':
        form = SolicitudClaseForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.alumno = alumno
            solicitud.maestro = maestro
            solicitud.estado = 'pendiente'
            solicitud.save()
            
            messages.success(request, '¡Solicitud enviada correctamente!')
            return redirect('mis_solicitudes_alumno')
    else:
        form = SolicitudClaseForm()
    
    return render(request, 'alumno/enviar_solicitud.html', {
        'form': form,
        'maestro': maestro
    })

@login_required
def mis_solicitudes_alumno(request):
    try:
        alumno = Alumno.objects.get(usuario=request.user)
        solicitudes = SolicitudClase.objects.filter(alumno=alumno).order_by('-fecha_solicitud')
        
        # Filtros
        estado_filtro = request.GET.get('estado', 'todas')
        if estado_filtro != 'todas':
            solicitudes = solicitudes.filter(estado=estado_filtro)
        
        contadores = {
            'todas': solicitudes.count(),
            'pendientes': solicitudes.filter(estado='pendiente').count(),
            'aceptadas': solicitudes.filter(estado='aceptada').count(),
            'rechazadas': solicitudes.filter(estado='rechazada').count(),
        }
        
    except Alumno.DoesNotExist:
        messages.error(request, "No tienes un perfil de alumno.")
        return redirect("dashboard_alumno")
    
    return render(request, "alumno/mis_solicitudes.html", {
        "solicitudes": solicitudes,
        "contadores": contadores,
        "estado_filtro": estado_filtro
    })

# VISTAS PARA MENSAJES

@login_required
def lista_conversaciones(request):
    conversaciones = []
    
    if request.user.rol == 'ALUMNO':
        alumno = get_object_or_404(Alumno, usuario=request.user)
        conversaciones = Conversacion.objects.filter(alumno=alumno).order_by('-ultimo_mensaje')
    elif request.user.rol == 'MAESTRO':
        maestro = get_object_or_404(Maestro, usuario=request.user)
        conversaciones = Conversacion.objects.filter(maestro=maestro).order_by('-ultimo_mensaje')
    
    return render(request, 'mensajes/lista_conversaciones.html', {
        'conversaciones': conversaciones
    })

@login_required
def ver_conversacion(request, conversacion_id):
    conversacion = get_object_or_404(Conversacion, id=conversacion_id)
    
    # Verificar que el usuario tiene permiso para ver esta conversación
    if request.user.rol == 'ALUMNO':
        alumno = get_object_or_404(Alumno, usuario=request.user)
        if conversacion.alumno != alumno:
            messages.error(request, "No tienes permiso para ver esta conversación.")
            return redirect('lista_conversaciones')
    elif request.user.rol == 'MAESTRO':
        maestro = get_object_or_404(Maestro, usuario=request.user)
        if conversacion.maestro != maestro:
            messages.error(request, "No tienes permiso para ver esta conversación.")
            return redirect('lista_conversaciones')
    
    mensajes = conversacion.mensajes.all().order_by('fecha_envio')
    
    if request.method == 'POST':
        form = MensajeForm(request.POST)
        if form.is_valid():
            mensaje = form.save(commit=False)
            mensaje.conversacion = conversacion
            mensaje.remitente = request.user
            mensaje.save()
            
            # Actualizar último mensaje de la conversación
            conversacion.ultimo_mensaje = timezone.now()
            conversacion.save()
            
            return redirect('ver_conversacion', conversacion_id=conversacion.id)
    else:
        form = MensajeForm()
    
    # Marcar mensajes como leídos
    mensajes.filter(leido=False).exclude(remitente=request.user).update(leido=True)
    
    return render(request, 'mensajes/conversacion.html', {
        'conversacion': conversacion,
        'mensajes': mensajes,
        'form': form
    })

@login_required
def iniciar_conversacion(request, usuario_id):
    usuario_destino = get_object_or_404(Usuario, id=usuario_id)
    
    if request.user.rol == 'ALUMNO':
        alumno = get_object_or_404(Alumno, usuario=request.user)
        maestro = get_object_or_404(Maestro, usuario=usuario_destino)
        
        conversacion, created = Conversacion.objects.get_or_create(
            alumno=alumno,
            maestro=maestro
        )
        
    elif request.user.rol == 'MAESTRO':
        maestro = get_object_or_404(Maestro, usuario=request.user)
        alumno = get_object_or_404(Alumno, usuario=usuario_destino)
        
        conversacion, created = Conversacion.objects.get_or_create(
            maestro=maestro,
            alumno=alumno
        )
    
    return redirect('ver_conversacion', conversacion_id=conversacion.id)

# Actualizar la vista detalle_maestro para incluir el botón de solicitud
@login_required
def detalle_maestro(request, maestro_id):
    maestro = get_object_or_404(Maestro, id=maestro_id)
    usuario = maestro.usuario
    
    # Verificar si ya existe una conversación
    tiene_conversacion = False
    if request.user.rol == 'ALUMNO':
        alumno = get_object_or_404(Alumno, usuario=request.user)
        tiene_conversacion = Conversacion.objects.filter(
            alumno=alumno, 
            maestro=maestro
        ).exists()
    
    return render(request, "alumno/detalle_maestro.html", {
        "maestro": maestro, 
        "usuario": usuario,
        "tiene_conversacion": tiene_conversacion
    })




# Vista para que el maestro proponga fecha y monto
@login_required
def proponer_fecha_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id)
    
    # Verificar que el maestro es el dueño de la solicitud
    if solicitud.maestro.usuario != request.user:
        messages.error(request, "No tienes permiso para esta acción.")
        return redirect('solicitudes_para_maestro')
    
    if request.method == 'POST':
        form = ProponerFechaForm(request.POST, instance=solicitud)
        if form.is_valid():
            try:
                solicitud = form.save(commit=False)
                # Cambiar estado a 'propuesta' en lugar de 'aceptada'
                solicitud.estado = 'propuesta'
                solicitud.save()
                
                # Crear notificación para el alumno
                crear_notificacion(
                    usuario=solicitud.alumno.usuario,
                    tipo='solicitud',
                    mensaje=f'El maestro {solicitud.maestro.usuario.get_full_name()} te ha propuesto una fecha para la clase de {solicitud.materia.nombre}',
                    enlace=f'/alumno/solicitudes/'
                )
                
                messages.success(request, '✅ Fecha y monto propuestos correctamente. El alumno recibió una notificación.')
                return redirect('solicitudes_para_maestro')
                
            except Exception as e:
                messages.error(request, f'❌ Error al guardar la propuesta: {str(e)}')
    else:
        form = ProponerFechaForm(instance=solicitud)
    
    return render(request, 'maestro/proponer_fecha.html', {
        'form': form,
        'solicitud': solicitud
    })

# Vista para que el alumno confirme la fecha
@login_required
def confirmar_fecha_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id)
    
    # Verificar que el alumno es el dueño de la solicitud y que está en estado 'propuesta'
    if solicitud.alumno.usuario != request.user:
        messages.error(request, "No tienes permiso para esta acción.")
        return redirect('mis_solicitudes_alumno')
    
    if solicitud.estado != 'propuesta':
        messages.error(request, "Esta solicitud no tiene una propuesta pendiente de confirmación.")
        return redirect('mis_solicitudes_alumno')
    
    if request.method == 'POST':
        form = ConfirmarFechaForm(request.POST, instance=solicitud)
        if form.is_valid():
            try:
                solicitud = form.save(commit=False)
                solicitud.estado = 'aceptada'  # Cambiar estado a aceptada
                solicitud.save()
                
                # Crear notificación para el maestro
                crear_notificacion(
                    usuario=solicitud.maestro.usuario,
                    tipo='clase_aceptada',
                    mensaje=f'El alumno {solicitud.alumno.usuario.get_full_name()} ha aceptado tu propuesta para la clase de {solicitud.materia.nombre}',
                    enlace=f'/maestro/solicitudes/'
                )
                
                messages.success(request, '✅ ¡Clase confirmada! La clase ha sido agendada.')
                
                # Redirigir a la página de pago si no es efectivo
                if solicitud.metodo_pago != 'efectivo':
                    return redirect('generar_qr_pago', solicitud_id=solicitud.id)
                else:
                    return redirect('mis_solicitudes_alumno')
                    
            except Exception as e:
                messages.error(request, f'❌ Error al confirmar la clase: {str(e)}')
    else:
        form = ConfirmarFechaForm(instance=solicitud)
    
    return render(request, 'alumno/confirmar_fecha.html', {
        'form': form,
        'solicitud': solicitud
    })

# Vista para generar código QR de Mercado Pago
@login_required
def generar_qr_pago(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id)
    
    # Verificar permisos
    if solicitud.alumno.usuario != request.user and solicitud.maestro.usuario != request.user:
        messages.error(request, "No tienes permiso para ver esta información.")
        return redirect('home')
    
    # Verificar que la clase esté aceptada
    if solicitud.estado != 'aceptada':
        messages.error(request, "Esta clase no está confirmada para generar pago.")
        return redirect('mis_solicitudes_alumno')
    
    try:
        if solicitud.metodo_pago == 'mercadopago':
            # Datos para Mercado Pago (simulación)
            monto = float(solicitud.monto_acordado) if solicitud.monto_acordado else 0
            descripcion = f"Clase de {solicitud.materia.nombre} con {solicitud.maestro.usuario.get_full_name()}"
            
            # En una implementación real, aquí integrarías con la API de Mercado Pago
            # Por ahora simulamos un enlace
            enlace_pago = f"https://www.mercadopago.com.mx/integrations/v1/web-payment-checkout.js?data-preference-id=simulado_{solicitud.id}"
            
            # Datos para el QR (simulando datos de Mercado Pago)
            qr_data = f"MP:{solicitud.maestro.usuario.id}:{monto}:{solicitud.id}"
            
        elif solicitud.metodo_pago == 'transferencia':
            # Datos para transferencia
            monto = float(solicitud.monto_acordado) if solicitud.monto_acordado else 0
            qr_data = f"TRANSFER:{solicitud.maestro.cbu_cvu_alias}:{monto}:{solicitud.maestro.usuario.get_full_name()}"
            enlace_pago = None
            
        else:  # efectivo
            qr_data = None
            enlace_pago = None
        
        # Generar QR si hay datos
        qr_image = None
        if qr_data:
            import qrcode
            from io import BytesIO
            import base64
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_image = base64.b64encode(buffer.getvalue()).decode()
        
    except Exception as e:
        messages.error(request, f"Error al generar código de pago: {str(e)}")
        qr_image = None
        enlace_pago = None
    
    return render(request, 'pagos/generar_qr.html', {
        'solicitud': solicitud,
        'qr_image': qr_image,
        'enlace_pago': enlace_pago
    })

# Vistas para disponibilidad/agenda
@login_required
def agenda_usuario(request):
    # Obtener eventos del usuario
    eventos = DisponibilidadUsuario.objects.filter(usuario=request.user).order_by('fecha_inicio')
    
    if request.method == 'POST':
        form = DisponibilidadForm(request.POST)
        if form.is_valid():
            try:
                evento = form.save(commit=False)
                evento.usuario = request.user
                evento.save()
                
                # Crear notificación de éxito
                messages.success(request, f'✅ Evento "{evento.titulo}" agregado correctamente a tu agenda.')
                return redirect('agenda_usuario')
                
            except Exception as e:
                messages.error(request, f'❌ Error al guardar el evento: {str(e)}')
        else:
            messages.error(request, '❌ Por favor, corrige los errores en el formulario.')
    
    else:
        form = DisponibilidadForm()

    # Obtener clases para el calendario
    if request.user.rol == 'ALUMNO':
        clases = SolicitudClase.objects.filter(
            alumno__usuario=request.user, 
            estado__in=['aceptada', 'completada'],
            fecha_clase_confirmada__isnull=False
        )
    else:  # MAESTRO
        clases = SolicitudClase.objects.filter(
            maestro__usuario=request.user,
            estado__in=['aceptada', 'completada'], 
            fecha_clase_confirmada__isnull=False
        )
    
    # Convertir eventos a formato calendario
    eventos_calendario = []
    
    # Agregar eventos de disponibilidad
    for evento in eventos:
        eventos_calendario.append({
            'title': f"📅 {evento.titulo}",
            'start': evento.fecha_inicio.isoformat(),
            'end': evento.fecha_fin.isoformat(),
            'color': '#28a745' if evento.tipo == 'disponible' else '#dc3545' if evento.tipo == 'ocupacion' else '#007bff',
            'textColor': 'white',
            'extendedProps': {
                'tipo': 'evento_personal',
                'descripcion': evento.descripcion or '',
                'id': evento.id,
                'tipo_display': evento.get_tipo_display()
            }
        })
    
    # Agregar clases al calendario
    for clase in clases:
        if request.user.rol == 'ALUMNO':
            titulo = f'🎓 Clase: {clase.materia.nombre}'
            descripcion = f"Profesor: {clase.maestro.usuario.get_full_name()}"
        else:
            titulo = f'👨‍🏫 Clase: {clase.materia.nombre}'
            descripcion = f"Alumno: {clase.alumno.usuario.get_full_name()}"
        
        fecha_fin = clase.fecha_clase_confirmada + timedelta(minutes=clase.duracion_minutos)
        
        eventos_calendario.append({
            'title': titulo,
            'start': clase.fecha_clase_confirmada.isoformat(),
            'end': fecha_fin.isoformat(),
            'color': '#ffc107',
            'textColor': 'black',
            'extendedProps': {
                'tipo': 'clase',
                'materia': clase.materia.nombre,
                'duracion': clase.duracion_minutos,
                'monto': float(clase.monto_acordado) if clase.monto_acordado else 0,
                'descripcion': descripcion,
                'id': clase.id
            }
        })
    
    return render(request, 'agenda/agenda_usuario.html', {
        'form': form,
        'eventos': eventos,
        'clases': clases,
        'eventos_calendario': json.dumps(eventos_calendario)
    })



