from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from .forms import RegistroPersonaForm, RegistroAlumnoForm, RegistroMaestroForm, ReseñaForm, LoginForm, UsuarioForm, AlumnoForm, ConfirmarFechaForm, DisponibilidadForm, ReseñaAlumnoForm, BlocNotasForm, TareaForm, SesionEstudioForm, NotaForm, PromocionForm, VoucherForm
from .models import Departamento, Municipio, Localidad, Provincia, Maestro, Alumno, Usuario, DisponibilidadUsuario, BlocNotas, Tarea, SesionEstudio, Nota, Promocion, Voucher
from catalogo.models import Materia
import math
from django.db.models.functions import Coalesce

from .utils import enviar_email
from django.contrib.auth.forms import PasswordResetForm

from .forms import EditarPerfilMaestroForm  # Asegúrate de importar el formulario
from .models import SolicitudClase, ReseñaAlumno
from django.db.models import Q  # Para búsquedas complejas
from django.utils import timezone
from .models import Conversacion, Mensaje
from .forms import SolicitudClaseForm, MensajeForm, ProponerFechaForm

from django.http import JsonResponse
from django.db.models import Count, Avg, Q, Sum, Exists, OuterRef
from .models import Notificacion, Reseña
import json
from datetime import datetime, timedelta

from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.shortcuts import redirect



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

def admin_required(function=None):
    """Decorator para verificar si el usuario es administrador"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (u.is_superuser or getattr(u, 'rol', '') == 'ADMIN'),
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


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

""" # Vista para agregar reseña
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
    }) """




""" ####################   COMO ANTES   ###########3# """
def home_view(request):
    total_profesores = Maestro.objects.count()
    total_materias = Materia.objects.count()
    
    total_clases = SolicitudClase.objects.filter(
        Q(estado='aceptada') | Q(estado='completada')
    ).count()

    # PROFESOR DESTACADO (mejor calificado)
    profesor_destacado = Maestro.objects.annotate(
        avg_rating=Avg('reseñas__puntuacion'),
        review_count=Count('reseñas'),
        total_clases=Count('solicitudclase', filter=Q(solicitudclase__estado='completada'))
    ).filter(
        avg_rating__isnull=False
    ).order_by('-avg_rating', '-review_count').first()

    # NUEVOS PROFESORES (última semana) - CORREGIDO
    una_semana_atras = timezone.now() - timedelta(days=7)
    nuevos_profesores = Maestro.objects.filter(
        usuario__fecha_creacion__gte=una_semana_atras
    ).annotate(
        avg_rating=Avg('reseñas__puntuacion'),
        review_count=Count('reseñas')
    ).select_related('usuario').order_by('-usuario__fecha_creacion')[:4]

    # Si no hay nuevos de la última semana, mostrar los últimos registrados
    if not nuevos_profesores:
        nuevos_profesores = Maestro.objects.annotate(
            avg_rating=Avg('reseñas__puntuacion'),
            review_count=Count('reseñas')
        ).select_related('usuario').order_by('-usuario__fecha_creacion')[:4]

    # PROFESOR POPULAR (más alumnos)
    profesores_con_alumnos = []
    for maestro in Maestro.objects.all():
        total_alumnos = SolicitudClase.objects.filter(
            maestro=maestro, 
            estado='aceptada'
        ).values('alumno').distinct().count()
        
        if total_alumnos > 0:
            profesores_con_alumnos.append({
                'maestro': maestro,
                'total_alumnos': total_alumnos
            })
    
    profesor_popular = None
    if profesores_con_alumnos:
        profesor_popular_data = sorted(
            profesores_con_alumnos, 
            key=lambda x: -x['total_alumnos']
        )[0]
        profesor_popular = profesor_popular_data['maestro']
        profesor_popular.total_alumnos = profesor_popular_data['total_alumnos']

    # MATERIAS POPULARES
    materias_populares = []
    for materia in Materia.objects.all():
        num_profesores = materia.maestros.count()
        if num_profesores > 0:
            materias_populares.append({
                'materia': materia,
                'num_profesores': num_profesores
            })
    
    materias_populares = sorted(
        materias_populares, 
        key=lambda x: -x['num_profesores']
    )[:6]

    # PROFESORES VERIFICADOS
    profesores_verificados = Maestro.objects.filter(
        usuario__verificado=True
    ).annotate(
        avg_rating=Avg('reseñas__puntuacion'),
        review_count=Count('reseñas')
    ).select_related('usuario')[:3]

    profesores_ultima_semana = Maestro.objects.filter(
        usuario__fecha_creacion__gte=una_semana_atras
    ).count()

    # ANUNCIOS SIMULADOS
    anuncios = [
        {
            'titulo': '🎓 Clase de Prueba Gratuita',
            'descripcion': '¡Agendá tu primera clase sin costo! Conocé a tu profesor ideal.',
            'color': 'primary',
            'icon': 'fa-graduation-cap'
        },
        {
            'titulo': '💰 20% OFF en Primera Clase',
            'descripcion': 'Descuento especial para nuevos estudiantes. ¡Aprovechá ahora!',
            'color': 'success',
            'icon': 'fa-tag'
        },
        {
            'titulo': '👥 Grupos de Estudio',
            'descripcion': 'Formá grupos y ahorrá hasta 30% en clases grupales.',
            'color': 'info',
            'icon': 'fa-users'
        },
        {
            'titulo': '🏆 Profesores Verificados',
            'descripcion': 'Todos nuestros profesores pasan por un riguroso proceso de verificación.',
            'color': 'warning',
            'icon': 'fa-shield-alt'
        }
    ]

    context = {
        'total_profesores': total_profesores,
        'total_materias': total_materias,
        'total_clases': total_clases,
        'profesor_destacado': profesor_destacado,
        'profesor_popular': profesor_popular,
        'nuevos_profesores': nuevos_profesores,
        'materias_populares': materias_populares,
        'profesores_verificados': profesores_verificados,
        'profesores_ultima_semana': profesores_ultima_semana,
        'anuncios': anuncios,
    }
    return render(request, "home.html", context)


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

    # 🔹 Obtenemos el perfil del alumno (OneToOne con Usuario)
    try:
        alumno = usuario.alumno
    except Alumno.DoesNotExist:
        messages.error(request, "No tienes un perfil de alumno.")
        return redirect("home")

    ahora = timezone.now()

    # 🔹 Estadísticas principales
    solicitudes_pendientes = SolicitudClase.objects.filter(
        alumno=alumno,
        estado="pendiente"
    ).count()

    fin_semana = ahora + timezone.timedelta(days=7)
    clases_esta_semana = SolicitudClase.objects.filter(
        alumno=alumno,
        estado="aceptada",
        fecha_clase_propuesta__gte=ahora,
        fecha_clase_propuesta__lte=fin_semana
    ).count()

    materias_activas = SolicitudClase.objects.filter(
        alumno=alumno,
        estado="aceptada"
    ).values("materia").distinct().count()

    # 🔹 Total gastado (solo clases pagadas)
    total_gastado = SolicitudClase.objects.filter(
        alumno=alumno,
        estado_pago="pagado"
    ).aggregate(Sum("monto_acordado"))["monto_acordado__sum"] or 0

    # 🔹 Próximas clases (usando Coalesce y Exists)
    resena_exists = Reseña.objects.filter(solicitud=OuterRef("pk"))

    proximas_clases = (
        SolicitudClase.objects
        .filter(alumno=alumno)
        .annotate(
            tiene_resena=Exists(resena_exists),
            fecha_orden=Coalesce("fecha_clase_confirmada", "fecha_clase_propuesta")
        )
        .filter(
            Q(estado__in=["pendiente", "propuesta", "aceptada"], fecha_orden__gte=ahora)
            | Q(estado="completada", tiene_resena=False)
        )
        .exclude(fecha_orden__isnull=True)
        .order_by("fecha_orden")[:5]
    )

    # 🔹 Solicitudes sin fecha (por confirmar)
    por_confirmar = (
        SolicitudClase.objects
        .filter(
            alumno=alumno,
            estado__in=["pendiente", "propuesta"],
            fecha_clase_propuesta__isnull=True,
            fecha_clase_confirmada__isnull=True
        )
        .order_by("-fecha_solicitud")[:5]
    )

    # 🔹 Conversaciones recientes
    conversaciones = Conversacion.objects.filter(alumno=alumno).prefetch_related("mensajes")
    mensajes_recientes = []
    mensajes_nuevos = 0
    for conv in conversaciones:
        ultimo = conv.mensajes.order_by("-fecha_envio").first()
        if ultimo:
            if not ultimo.leido and ultimo.remitente != request.user:
                mensajes_nuevos += 1
            mensajes_recientes.append((conv, ultimo))

    # 🔹 Notificaciones no leídas
    notificaciones_no_leidas = Notificacion.objects.filter(
        usuario=request.user,
        leida=False
    ).count()

    # 🔹 Render final
    context = {
        "solicitudes_pendientes": solicitudes_pendientes,
        "clases_esta_semana": clases_esta_semana,
        "materias_activas": materias_activas,
        "total_gastado": total_gastado,
        "proximas_clases": proximas_clases,
        "por_confirmar": por_confirmar,
        "mensajes_recientes": mensajes_recientes,
        "mensajes_nuevos": mensajes_nuevos,
        "notificaciones_no_leidas": notificaciones_no_leidas,
    }

    return render(request, "cuentas/dashboard_alumno.html", context)


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

# AGREGAR ESTOS CÁLCULOS PARA GASTOS:
    solicitudes_con_pago = SolicitudClase.objects.filter(
        alumno=alumno
    ).exclude(monto_acordado__isnull=True)
    
    total_gastado = sum(
        float(s.monto_acordado) for s in solicitudes_con_pago.filter(estado_pago='pagado') 
        if s.monto_acordado
    )
    
    total_pendiente = sum(
        float(s.monto_acordado) for s in solicitudes_con_pago.filter(estado_pago='pendiente', estado='aceptada') 
        if s.monto_acordado
    )

    context = {
        "solicitudes_pendientes": solicitudes_pendientes,
        "clases_esta_semana": clases_esta_semana,
        "materias_activas": materias_activas,
        "proximas_clases": proximas_clases,
        "mensajes_recientes": mensajes_recientes,
        "mensajes_nuevos": mensajes_nuevos,
        "total_gastado": total_gastado,  # ← Esto debe estar
        "total_pendiente": total_pendiente,  # ← Y esto también
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

    # Solicitudes pendientes
    solicitudes_pendientes = SolicitudClase.objects.filter(
        maestro=perfil_maestro,
        estado="pendiente"
    ).count()

    # Clases esta semana
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

    # INGRESOS - cálculo detallado
    mes_actual = ahora.month
    año_actual = ahora.year

    solicitudes_aceptadas_mes = SolicitudClase.objects.filter(
        maestro=perfil_maestro,
        estado="aceptada",
        fecha_clase_propuesta__month=mes_actual,
        fecha_clase_propuesta__year=año_actual
    )

    ingresos_mes = 0
    for solicitud in solicitudes_aceptadas_mes:
        if solicitud.monto_acordado:
            ingresos_mes += float(solicitud.monto_acordado)

    count_clases_mes = solicitudes_aceptadas_mes.count()
    promedio_por_clase_mes = ingresos_mes / count_clases_mes if count_clases_mes > 0 else 0

    # Comparación con mes anterior
    if mes_actual == 1:
        mes_anterior = 12
        año_anterior = año_actual - 1
    else:
        mes_anterior = mes_actual - 1
        año_anterior = año_actual

    ingresos_mes_anterior = 0
    solicitudes_mes_anterior = SolicitudClase.objects.filter(
        maestro=perfil_maestro,
        estado="aceptada",
        fecha_clase_propuesta__month=mes_anterior,
        fecha_clase_propuesta__year=año_anterior
    )

    for solicitud in solicitudes_mes_anterior:
        if solicitud.monto_acordado:
            ingresos_mes_anterior += float(solicitud.monto_acordado)

    if ingresos_mes_anterior > 0:
        porcentaje_cambio_ingresos = ((ingresos_mes - ingresos_mes_anterior) / ingresos_mes_anterior) * 100
    else:
        porcentaje_cambio_ingresos = 100 if ingresos_mes > 0 else 0

    # Próximas clases
    resena_exists = ReseñaAlumno.objects.filter(solicitud=OuterRef('pk'))
    proximas_clases = (
        SolicitudClase.objects
        .filter(maestro=perfil_maestro)
        .annotate(
            tiene_resena=Exists(resena_exists),
            fecha_orden=Coalesce('fecha_clase_confirmada', 'fecha_clase_propuesta')
        )
        .filter(
            Q(estado__in=['pendiente', 'propuesta', 'aceptada'], fecha_orden__gte=ahora)
            | Q(estado='completada', tiene_resena=False)
        )
        .exclude(fecha_orden__isnull=True)
        .order_by('fecha_orden')[:5]
    )

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

    # Tareas del usuario
    total_tareas = request.user.tarea_set.count()
    tareas_pendientes = request.user.tarea_set.filter(completada=False).count()
    tareas_completadas = request.user.tarea_set.filter(completada=True).count()

    context = {
        "solicitudes_pendientes": solicitudes_pendientes,
        "clases_esta_semana": clases_esta_semana,
        "clases_hoy": clases_hoy,
        "ingresos_mes": round(ingresos_mes, 2),
        "count_clases_mes": count_clases_mes,
        "promedio_por_clase_mes": round(promedio_por_clase_mes, 2),
        "porcentaje_cambio_ingresos": round(porcentaje_cambio_ingresos, 1),
        "proximas_clases": proximas_clases,
        "mensajes_recientes": mensajes_recientes,
        "mensajes_nuevos": mensajes_nuevos,
        "notificaciones_no_leidas": notificaciones_no_leidas,
        "total_tareas": total_tareas,
        "tareas_pendientes": tareas_pendientes,
        "tareas_completadas": tareas_completadas,
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

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render
from django.db.models import Q, Avg, Count
from django.contrib.auth import get_user_model

from .permissions import puede_ver_perfil_alumno
from .models import SolicitudClase  # ReseñaAlumno lo manejamos abajo de forma flexible

Usuario = get_user_model()

# Importa tus modelos Maestro/Alumno
from .models import Alumno  # existe en tu código

# --- utilidades ---

def _rol(u):
    return str(getattr(u, "rol", "")).upper()

def _get_alumno_user_or_404(alumno_id: int) -> Usuario:
    """
    Acepta tanto Usuario.id como Alumno.id y devuelve siempre el Usuario.
    """
    # 1) ¿es un Usuario.id?
    usuario = Usuario.objects.filter(pk=alumno_id).first()
    if usuario:
        return usuario
    # 2) ¿es un Alumno.id?
    alumno_obj = Alumno.objects.filter(pk=alumno_id).select_related("usuario").first()
    if alumno_obj:
        return alumno_obj.usuario
    raise Http404("Alumno no encontrado")

# --- vista ---

@login_required
def perfil_alumno(request, alumno_id):
    """
    Perfil del Alumno para que un Maestro (con relación) lo vea.
    También puede verlo el propio alumno y admin.
    """
    # Siempre resolvemos a Usuario
    alumno_user = _get_alumno_user_or_404(alumno_id)

    # Traer objeto Alumno (para bio/teléfono si lo usás ahí)
    alumno_obj = Alumno.objects.filter(usuario=alumno_user).first()

    # Permisos
    if not puede_ver_perfil_alumno(request.user, alumno_user):
        return HttpResponseForbidden("No tenés permisos para ver este perfil.")

    # --- Reseñas ---
    # Tu Alumno tiene related_name "reseñas_recibidas", así que lo habitual es que
    # ReseñaAlumno.alumno apunte a Alumno. Por si acaso contemplamos ambos casos.
    try:
        from .models import ReseñaAlumno  # si existe en tu app
        reseñas_qs = ReseñaAlumno.objects.filter(
            Q(alumno=alumno_obj) | Q(alumno__usuario=alumno_user)
        ).select_related()
        promedio = reseñas_qs.aggregate(prom=Avg("puntuacion"))["prom"] or 0
        total_resenas = reseñas_qs.aggregate(c=Count("id"))["c"]
        reseñas = list(reseñas_qs[:10])
    except Exception:
        # Si no tenés el modelo aún, que no rompa
        promedio, total_resenas, reseñas = 0, 0, []
    
    # --- Historial con el maestro logueado ---
    es_maestro = _rol(request.user) in ("MAESTRO", "PROFESOR")
    historial_con_este_maestro = []
    if es_maestro:
        historial_con_este_maestro = SolicitudClase.objects.filter(
            Q(maestro__usuario=request.user) &
            Q(alumno__usuario=alumno_user) &
            Q(estado="aceptada")
        ).order_by("-fecha_solicitud")[:10]

    # --- Contacto visible sólo si hay clase aceptada ---
    mostrar_contacto = False
    if es_maestro:
        mostrar_contacto = SolicitudClase.objects.filter(
            Q(maestro__usuario=request.user) &
            Q(alumno__usuario=alumno_user) &
            Q(estado="aceptada")
        ).exists()

    ctx = {
        "alumno": alumno_obj,               # Alumno (puede ser None si faltara)
        "alumno_user": alumno_user,         # Usuario (siempre)
        "reseñas": reseñas,
        "promedio": round(promedio, 2) if promedio else 0,
        "total_resenas": total_resenas,
        "historial_con_este_maestro": historial_con_este_maestro,
        "mostrar_contacto": mostrar_contacto,
    }
    return render(request, "maestro/perfil_alumno.html", ctx)


from django.db.models import Q  # 👈 importante arriba del archivo
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def solicitudes_para_maestro(request):
    try:
        # Perfil del maestro logueado
        perfil_maestro = Maestro.objects.get(usuario=request.user)
        
        # Base: todas las solicitudes hacia este maestro
        solicitudes = SolicitudClase.objects.filter(
            maestro=perfil_maestro
        ).order_by('-fecha_solicitud')
        
        # --- Filtro por estado ---
        estado_filtro = request.GET.get('estado', 'todas')
        if estado_filtro != 'todas':
            solicitudes = solicitudes.filter(estado=estado_filtro)

        # --- Filtro por búsqueda (alumno o materia) ---
        query = request.GET.get('q', '').strip()
        if query:
            solicitudes = solicitudes.filter(
                Q(alumno__usuario__nombre__icontains=query) |
                Q(alumno__usuario__apellido__icontains=query) |
                Q(alumno__usuario__username__icontains=query) |
                Q(materia__nombre__icontains=query)
            )

        # Contadores para los badges (sin filtros, totales reales)
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
        "estado_filtro": estado_filtro,
        "query": query,
    })


@login_required
def dejar_reseña_alumno(request, solicitud_id):
    # 1. Buscamos esa clase, asegurándonos de que:
    #    - Pertenece a ESTE maestro logueado
    #    - Está completada (ya se dictó)
    solicitud = get_object_or_404(
        SolicitudClase,
        id=solicitud_id,
        maestro__usuario=request.user,
        estado='completada'
    )

    # 2. ¿Ya se calificó al alumno para esta clase?
    #    Evitamos reseña duplicada.
    if hasattr(solicitud, 'reseña_alumno'):
        messages.info(request, "Ya calificaste a este alumno para esta clase.")
        return redirect('dashboard_maestro')

    # 3. Manejo del formulario
    if request.method == 'POST':
        form = ReseñaAlumnoForm(request.POST)
        if form.is_valid():
            reseña_alumno = form.save(commit=False)
            reseña_alumno.solicitud = solicitud
            reseña_alumno.maestro = solicitud.maestro
            reseña_alumno.alumno = solicitud.alumno
            reseña_alumno.save()

            messages.success(request, "Reseña del alumno registrada ✅")
            return redirect('dashboard_maestro')
    else:
        form = ReseñaAlumnoForm()

    # 4. Renderizar el formulario de calificación
    return render(request, 'reseñas/dejar_reseña_alumno.html', {
        'form': form,
        'solicitud': solicitud,
    })



@login_required
def cambiar_estado_solicitud(request, solicitud_id, nuevo_estado):
    try:
        perfil_maestro = Maestro.objects.get(usuario=request.user)
        solicitud = SolicitudClase.objects.get(id=solicitud_id, maestro=perfil_maestro)

        # Estados válidos para cambiar
        estados_validos = ['aceptada', 'rechazada', 'cancelada']
        
        if nuevo_estado in estados_validos:
            # Si es aceptada, verificar que tenga fecha propuesta
            if nuevo_estado == 'aceptada' and not solicitud.fecha_clase_propuesta:
                messages.error(request, "Debes proponer una fecha antes de aceptar la solicitud.")
                return redirect('solicitudes_para_maestro')
                
            solicitud.estado = nuevo_estado
            solicitud.save()
            messages.success(request, f"Solicitud {nuevo_estado} correctamente.")

            # Envío de notificaciones y correos (mantener tu código existente)
            alumno = solicitud.alumno
            maestro = solicitud.maestro

            if nuevo_estado == 'aceptada':
                # Código de notificación para aceptada...
                pass
            elif nuevo_estado == 'rechazada':
                # Código de notificación para rechazada...
                pass

        else:
            messages.error(request, "Estado no válido.")
            
    except SolicitudClase.DoesNotExist:
        messages.error(request, "Solicitud no encontrada.")
    except Maestro.DoesNotExist:
        messages.error(request, "No tienes permiso para esta acción.")
    
    return redirect("solicitudes_para_maestro")

@login_required
def dejar_reseña_alumno(request, solicitud_id):
    # 1. Buscamos esa clase, asegurándonos de que:
    #    - Pertenece a ESTE maestro logueado
    #    - Está completada (ya se dictó)
    solicitud = get_object_or_404(
        SolicitudClase,
        id=solicitud_id,
        maestro__usuario=request.user,
        estado='completada'
    )

    # 2. ¿Ya se calificó al alumno para esta clase?
    #    Evitamos reseña duplicada.
    if hasattr(solicitud, 'reseña_alumno'):
        messages.info(request, "Ya calificaste a este alumno para esta clase.")
        return redirect('dashboard_maestro')

    # 3. Manejo del formulario
    if request.method == 'POST':
        form = ReseñaAlumnoForm(request.POST)
        if form.is_valid():
            reseña_alumno = form.save(commit=False)
            reseña_alumno.solicitud = solicitud
            reseña_alumno.maestro = solicitud.maestro
            reseña_alumno.alumno = solicitud.alumno
            reseña_alumno.save()

            messages.success(request, "Reseña del alumno registrada ✅")
            return redirect('dashboard_maestro')
    else:
        form = ReseñaAlumnoForm()

    # 4. Renderizar el formulario de calificación
    return render(request, 'reseñas/dejar_reseña_alumno.html', {
        'form': form,
        'solicitud': solicitud,
    })

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
        "usuario": request.user,
        "usuario_maestro": request.user,  # ✅ agregado
    })


# También necesitamos una vista pública para que otros usuarios vean el perfil
def perfil_maestro_publico(request, maestro_id):
    maestro = get_object_or_404(Maestro, id=maestro_id)
    usuario_maestro = maestro.usuario
    
    clases_impartidas = SolicitudClase.objects.filter(
        maestro=maestro, 
        estado__in=['aceptada', 'completada']
    ).count()
    
    alumnos_unicos = SolicitudClase.objects.filter(
        maestro=maestro, 
        estado__in=['aceptada', 'completada']
    ).values('alumno').distinct().count()
    
    es_propio_perfil = request.user.is_authenticated and request.user == usuario_maestro
    es_alumno_autenticado = request.user.is_authenticated and request.user.rol == 'ALUMNO'
    
    mostrar_info_completa = es_propio_perfil or es_alumno_autenticado
    
    if es_propio_perfil:
        template_name = "maestro/perfil_publico_maestro.html"
    else:
        template_name = "maestro/perfil_maestro_publico.html"
    
    context = {
        'maestro': maestro,
        'usuario_maestro': usuario_maestro,
        'clases_impartidas': clases_impartidas,
        'alumnos_unicos': alumnos_unicos,
        'mostrar_info_completa': mostrar_info_completa,
        'es_propio_perfil': es_propio_perfil,
    }
    
    return render(request, template_name, context)




# VISTAS PARA ALUMNO - SOLICITUDES

@login_required
def enviar_solicitud_clase(request, maestro_id):
    maestro = get_object_or_404(Maestro, id=maestro_id)
    alumno = get_object_or_404(Alumno, usuario=request.user)

    if request.method == 'POST':
        form = SolicitudClaseForm(request.POST, maestro=maestro)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.alumno = alumno
            solicitud.maestro = maestro
            solicitud.estado = 'pendiente'
            solicitud.save()
            messages.success(request, '¡Solicitud enviada correctamente!')
            return redirect('mis_solicitudes_alumno')
    else:
        form = SolicitudClaseForm(maestro=maestro)

    return render(request, 'alumno/enviar_solicitud.html', {
        'form': form,
        'maestro': maestro
    })

@login_required
def mis_solicitudes_alumno(request):
    try:
        alumno = Alumno.objects.get(usuario=request.user)
        solicitudes = SolicitudClase.objects.filter(alumno=alumno).order_by('-fecha_solicitud')
        
        # --- Filtro por estado ---
        estado_filtro = request.GET.get('estado', 'todas')
        if estado_filtro != 'todas':
            solicitudes = solicitudes.filter(estado=estado_filtro)

        # --- NUEVO: Filtro de búsqueda por maestro o materia ---
        query = request.GET.get('q', '').strip()
        if query:
            solicitudes = solicitudes.filter(
                Q(maestro__usuario__nombre__icontains=query) |
                Q(maestro__usuario__apellido__icontains=query) |
                Q(maestro__usuario__username__icontains=query) |
                Q(materia__nombre__icontains=query)
            )

        # --- Contadores ---
        contadores = {
            'todas': SolicitudClase.objects.filter(alumno=alumno).count(),
            'pendientes': SolicitudClase.objects.filter(alumno=alumno, estado='pendiente').count(),
            'aceptadas': SolicitudClase.objects.filter(alumno=alumno, estado='aceptada').count(),
            'rechazadas': SolicitudClase.objects.filter(alumno=alumno, estado='rechazada').count(),
        }
        
    except Alumno.DoesNotExist:
        messages.error(request, "No tienes un perfil de alumno.")
        return redirect("dashboard_alumno")
    
    return render(request, "alumno/mis_solicitudes.html", {
        "solicitudes": solicitudes,
        "contadores": contadores,
        "estado_filtro": estado_filtro,
        "query": query,  # 👈 Para mantener el valor del input
    })
# VISTAS PARA MENSAJES

@login_required
def lista_conversaciones(request):
    conversaciones = []
    total_mensajes_no_leidos = 0
    total_archivos = 0
    
    if request.user.rol == 'ALUMNO':
        alumno = get_object_or_404(Alumno, usuario=request.user)
        conversaciones = Conversacion.objects.filter(alumno=alumno).order_by('-ultimo_mensaje')
        
        # Contar mensajes no leídos y archivos
        for conv in conversaciones:
            mensajes_no_leidos = conv.mensajes.filter(leido=False).exclude(remitente=request.user).count()
            total_mensajes_no_leidos += mensajes_no_leidos
            total_archivos += conv.mensajes.filter(tipo__in=['imagen', 'archivo']).count()
            
    elif request.user.rol == 'MAESTRO':
        maestro = get_object_or_404(Maestro, usuario=request.user)
        conversaciones = Conversacion.objects.filter(maestro=maestro).order_by('-ultimo_mensaje')
        
        # Contar mensajes no leídos y archivos
        for conv in conversaciones:
            mensajes_no_leidos = conv.mensajes.filter(leido=False).exclude(remitente=request.user).count()
            total_mensajes_no_leidos += mensajes_no_leidos
            total_archivos += conv.mensajes.filter(tipo__in=['imagen', 'archivo']).count()
    
    return render(request, 'mensajes/lista_conversaciones.html', {
        'conversaciones': conversaciones,
        'total_mensajes_no_leidos': total_mensajes_no_leidos,
        'total_archivos': total_archivos,
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
        form = MensajeForm(request.POST, request.FILES)
        if form.is_valid():
            mensaje = form.save(commit=False)
            mensaje.conversacion = conversacion
            mensaje.remitente = request.user
            
            # Determinar el tipo de mensaje
            if mensaje.imagen:
                mensaje.tipo = 'imagen'
                mensaje.nombre_archivo = mensaje.imagen.name
                mensaje.tamano_archivo = mensaje.imagen.size
            elif mensaje.archivo:
                mensaje.tipo = 'archivo'
                mensaje.nombre_archivo = mensaje.archivo.name
                mensaje.tamano_archivo = mensaje.archivo.size
            
            mensaje.save()
            
            # Actualizar último mensaje de la conversación
            conversacion.ultimo_mensaje = timezone.now()
            conversacion.save()
            
            # Si es una petición AJAX, devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'mensaje_id': mensaje.id
                })
            
            return redirect('ver_conversacion', conversacion_id=conversacion.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
    
    else:
        form = MensajeForm()
    
    # Marcar mensajes como leídos
    mensajes.filter(leido=False).exclude(remitente=request.user).update(leido=True)
    
    # Obtener estadísticas de archivos
    archivos_compartidos = mensajes.filter(tipo__in=['imagen', 'archivo'])
    
    return render(request, 'mensajes/conversacion.html', {
        'conversacion': conversacion,
        'mensajes': mensajes,
        'form': form,
        'archivos_compartidos': archivos_compartidos
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



def proponer_fecha_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id)
    
    if request.method == "POST":
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
                    mensaje=f"El maestro {solicitud.maestro.usuario.get_full_name()} te ha propuesto una fecha para la clase de {solicitud.materia.nombre}",
                    enlace='/alumno/solicitudes/'
                )

                messages.success(request, "✅ Fecha y monto propuestos correctamente. El alumno recibió una notificación.")
                return redirect('solicitudes_para_maestro')

            except Exception as e:
                messages.error(request, f"❌ Error al guardar la propuesta: {str(e)}")
        else:
            messages.error(request, "⚠️ El formulario no es válido.")
    else:
        form = ProponerFechaForm(instance=solicitud)

    return render(request, 'maestro/proponer_fecha.html', {'form': form, 'solicitud': solicitud})





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
                solicitud.estado = 'aceptada'
                
                # ✅ INICIALIZAR EL ESTADO DEL PAGO CORRECTAMENTE
                solicitud.estado_pago = 'pendiente'  # Esto es crucial
                
                # Si no se modifica la fecha, usar la propuesta por defecto
                if not solicitud.fecha_clase_confirmada:
                    solicitud.fecha_clase_confirmada = solicitud.fecha_clase_propuesta
                
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
                    # ✅ Para pagos en efectivo, redirigir al control de gastos
                    return redirect('control_gastos_alumno')
                    
            except Exception as e:
                messages.error(request, f'❌ Error al confirmar la clase: {str(e)}')
    else:
        # Inicializar con la fecha propuesta
        initial_data = {
            'fecha_clase_confirmada': solicitud.fecha_clase_propuesta,
            'metodo_pago': solicitud.metodo_pago
        }
        form = ConfirmarFechaForm(instance=solicitud, initial=initial_data)
    
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
    
    # ✅ Asegurarnos de que el estado de pago esté inicializado
    if not solicitud.estado_pago or solicitud.estado_pago == '':
        solicitud.estado_pago = 'pendiente'
        solicitud.save()
    
    try:
        qr_image = None
        enlace_pago = None
        datos_pago = {}
        
        if solicitud.metodo_pago == 'mercadopago':
            monto = float(solicitud.monto_acordado) if solicitud.monto_acordado else 0
            descripcion = f"Clase de {solicitud.materia.nombre} con {solicitud.maestro.usuario.get_full_name()}"
            
            # Simulación de datos de Mercado Pago
            datos_pago = {
                'tipo': 'mercadopago',
                'monto': monto,
                'descripcion': descripcion,
                'vendedor': solicitud.maestro.usuario.get_full_name(),
                'email_vendedor': solicitud.maestro.usuario.email,
            }
            
            # Generar QR para Mercado Pago (simulado)
            qr_data = f"mercadopago://payment?amount={monto}&description={descripcion}"
            
        elif solicitud.metodo_pago == 'transferencia':
            # Datos para transferencia
            monto = float(solicitud.monto_acordado) if solicitud.monto_acordado else 0
            datos_pago = {
                'tipo': 'transferencia',
                'monto': monto,
                'beneficiario': solicitud.maestro.usuario.get_full_name(),
                'cbu_cvu': solicitud.maestro.cbu_cvu_alias or "No especificado",
                'concepto': f"Clase {solicitud.materia.nombre} - {solicitud.fecha_clase_confirmada.strftime('%d/%m/%Y')}",
            }
            
            qr_data = f"TRANSFER:{solicitud.maestro.cbu_cvu_alias}:{monto}:{solicitud.maestro.usuario.get_full_name()}"
            enlace_pago = None
            
        else:  # efectivo
            datos_pago = {
                'tipo': 'efectivo',
                'monto': float(solicitud.monto_acordado) if solicitud.monto_acordado else 0,
                'instrucciones': 'Acordar pago en efectivo al momento de la clase',
            }
            qr_data = None
        
        # Generar QR si hay datos
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
        datos_pago = {}
    
    return render(request, 'pagos/generar_qr.html', {
        'solicitud': solicitud,
        'qr_image': qr_image,
        'datos_pago': datos_pago
    })

# Vistas para disponibilidad/agenda
@login_required
def agenda_usuario(request):
    # Obtener eventos del usuario
    eventos = DisponibilidadUsuario.objects.filter(usuario=request.user).order_by('fecha_inicio')
    
    # Obtener clases para el calendario
    if request.user.rol == 'ALUMNO':
        clases = SolicitudClase.objects.filter(
            alumno__usuario=request.user,
            estado='aceptada'
        )
    else:  # MAESTRO
        clases = SolicitudClase.objects.filter(
            maestro__usuario=request.user,
            estado='aceptada'
        )

    # Convertir eventos a formato calendario - FORMATO CORRECTO
    eventos_calendario = []
    
    # Agregar eventos de disponibilidad
    for evento in eventos:
        eventos_calendario.append({
            'id': f"disponibilidad_{evento.id}",
            'title': evento.titulo,
            'start': evento.fecha_inicio.isoformat(),
            'end': evento.fecha_fin.isoformat(),
            'color': get_event_color(evento.tipo),
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
        fecha_clase = clase.fecha_clase_confirmada or clase.fecha_clase_propuesta
        if not fecha_clase:
            continue

        if request.user.rol == 'ALUMNO':
            titulo = f'Clase: {clase.materia.nombre}'
            descripcion = f"Profesor: {clase.maestro.usuario.get_full_name()}"
        else:
            titulo = f'Clase: {clase.materia.nombre}'
            descripcion = f"Alumno: {clase.alumno.usuario.get_full_name()}"
        
        fecha_fin = fecha_clase + timedelta(minutes=clase.duracion_minutos)
        
        eventos_calendario.append({
            'id': f"clase_{clase.id}",
            'title': titulo,
            'start': fecha_clase.isoformat(),
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

    # Pasar los eventos como lista Python, no como JSON
    eventos_json = json.dumps(eventos_calendario)

    # Manejar el formulario de eventos
    if request.method == 'POST':
        form = DisponibilidadForm(request.POST)
        if form.is_valid():
            try:
                evento = form.save(commit=False)
                evento.usuario = request.user
                evento.save()
                messages.success(request, f'Evento "{evento.titulo}" agregado correctamente.')
                return redirect('agenda_usuario')
            except Exception as e:
                messages.error(request, f'Error al guardar el evento: {str(e)}')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = DisponibilidadForm()

    context = {
        'form': form,
        'eventos': eventos,
        'clases': clases,
        'eventos_json': eventos_json,  # Cambiado el nombre
        'rol': request.user.rol,
    }
    
    return render(request, 'agenda/agenda_usuario.html', context)

def get_event_color(tipo_evento):
    """Asigna colores según el tipo de evento"""
    colores = {
        'clase': '#28a745',      # Verde
        'ocupacion': '#dc3545',  # Rojo
        'disponible': '#007bff', # Azul
    }
    return colores.get(tipo_evento, '#6c757d')



from django.http import HttpResponse
from django.utils import timezone
import json

@login_required
def exportar_calendario_ics(request):
    """Exportar calendario a formato ICS para Google Calendar"""
    
    # Obtener eventos del usuario
    eventos = DisponibilidadUsuario.objects.filter(usuario=request.user)
    clases = SolicitudClase.objects.filter(
        Q(alumno__usuario=request.user) | Q(maestro__usuario=request.user),
        estado='aceptada',
        fecha_clase_confirmada__isnull=False
    )
    
    # Generar contenido ICS
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//EduLink//Calendario//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    # Agregar eventos de disponibilidad
    for evento in eventos:
        ics_content.extend([
            "BEGIN:VEVENT",
            f"UID:disponibilidad_{evento.id}@edulink.com",
            f"DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{evento.fecha_inicio.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{evento.fecha_fin.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{evento.titulo}",
            f"DESCRIPTION:{evento.descripcion or 'Evento de disponibilidad'}",
            f"LOCATION:EduLink",
            "END:VEVENT"
        ])
    
    # Agregar clases
    for clase in clases:
        if clase.fecha_clase_confirmada:
            fecha_fin = clase.fecha_clase_confirmada + timedelta(minutes=clase.duracion_minutos)
            titulo = f"Clase: {clase.materia.nombre}"
            descripcion = f"Clase de {clase.materia.nombre} con "
            
            if request.user.rol == 'ALUMNO':
                descripcion += f"Profesor: {clase.maestro.usuario.get_full_name()}"
            else:
                descripcion += f"Alumno: {clase.alumno.usuario.get_full_name()}"
            
            ics_content.extend([
                "BEGIN:VEVENT",
                f"UID:clase_{clase.id}@edulink.com",
                f"DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{clase.fecha_clase_confirmada.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{fecha_fin.strftime('%Y%m%dT%H%M%SZ')}",
                f"SUMMARY:{titulo}",
                f"DESCRIPTION:{descripcion}",
                f"LOCATION:EduLink",
                "END:VEVENT"
            ])
    
    ics_content.append("END:VCALENDAR")
    
    # Crear respuesta
    response = HttpResponse("\r\n".join(ics_content), content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename="edulink-calendario.ics"'
    
    return response




@login_required
def imprimir_agenda(request, vista='month'):
    """Vista simplificada para imprimir la agenda"""
    
    # Obtener eventos del usuario
    eventos = DisponibilidadUsuario.objects.filter(usuario=request.user).order_by('fecha_inicio')
    
    # Obtener clases
    if request.user.rol == 'ALUMNO':
        clases = SolicitudClase.objects.filter(
            alumno__usuario=request.user,
            estado='aceptada'
        )
    else:
        clases = SolicitudClase.objects.filter(
            maestro__usuario=request.user,
            estado='aceptada'
        )

    context = {
        'eventos': eventos,
        'clases': clases,
        'usuario': request.user,
        'fecha_impresion': timezone.now().date(),
        'vista': vista
    }
    
    return render(request, 'agenda/imprimir_agenda.html', context)




# En views.py - SOLO PARA DEBUG
@login_required
def debug_eventos(request):
    eventos = DisponibilidadUsuario.objects.filter(usuario=request.user)
    clases = SolicitudClase.objects.filter(
        Q(alumno__usuario=request.user) | Q(maestro__usuario=request.user),
        estado='aceptada'
    )
    
    print("=== DEBUG EVENTOS ===")
    print(f"Eventos personales: {eventos.count()}")
    print(f"Clases: {clases.count()}")
    
    for evento in eventos:
        print(f"Evento: {evento.titulo} - {evento.fecha_inicio} a {evento.fecha_fin}")
    
    for clase in clases:
        print(f"Clase: {clase.materia.nombre} - {clase.fecha_clase_propuesta}")
    
    return JsonResponse({
        'eventos_count': eventos.count(),
        'clases_count': clases.count(),
        'eventos': list(eventos.values('titulo', 'fecha_inicio', 'fecha_fin')),
        'clases': list(clases.values('materia__nombre', 'fecha_clase_propuesta'))
    })

############## FUNCIONES DE RESEÑA ##########################

@login_required
def marcar_completada(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id, maestro__usuario=request.user)
    if solicitud.estado == 'aceptada':
        solicitud.estado = 'completada'
        solicitud.save()
        messages.success(request, "Clase marcada como completada ✅")
    else:
        messages.warning(request, "No se puede marcar esta clase como completada.")
    return redirect('solicitudes_para_maestro')

# ⭐ DEJAR RESEÑA (Alumno)
@login_required
def dejar_reseña(request, solicitud_id):
    solicitud = get_object_or_404(
        SolicitudClase,
        id=solicitud_id,
        alumno__usuario=request.user,
        estado='completada'
    )

    # Evitar reseñas duplicadas
    if hasattr(solicitud, 'reseña'):
        messages.info(request, "Ya enviaste una reseña para esta clase.")
        return redirect('dashboard_alumno')

    if request.method == 'POST':
        form = ReseñaForm(request.POST)
        if form.is_valid():
            reseña = form.save(commit=False)
            reseña.solicitud = solicitud
            reseña.alumno = solicitud.alumno
            reseña.maestro = solicitud.maestro
            reseña.save()
            messages.success(request, "¡Gracias por tu reseña!")
            return redirect('dashboard_alumno')
    else:
        form = ReseñaForm()

    return render(request, 'reseñas/dejar_reseña.html', {
        'form': form,
        'solicitud': solicitud,
    })




@login_required
def control_gastos_alumno(request):
    """Vista principal del control de gastos del alumno - MEJORADA CON DEBUG"""
    try:
        alumno = Alumno.objects.get(usuario=request.user)
        

         # Obtener parámetros de filtro
        mes = request.GET.get('mes')
        año = request.GET.get('año', timezone.now().year)


        # Obtener TODAS las solicitudes con montos
        solicitudes = SolicitudClase.objects.filter(
            alumno=alumno
        ).exclude(monto_acordado__isnull=True).select_related(
            'maestro', 'maestro__usuario', 'materia'
        ).order_by('-fecha_solicitud')
        

        # Aplicar filtros
        if mes and año:
            try:
                solicitudes = solicitudes.filter(
                    fecha_solicitud__year=año,
                    fecha_solicitud__month=mes
                )
            except ValueError:
                pass


        # DEBUG DETALLADO
        print(f"=== DEBUG CONTROL GASTOS ===")
        print(f"Solicitudes encontradas: {solicitudes.count()}")
        for s in solicitudes:
            print(f"- ID: {s.id} | Materia: {s.materia.nombre} | Monto: ${s.monto_acordado} | Estado: {s.estado} | Estado Pago: {s.estado_pago} | Fecha: {s.fecha_clase_propuesta}")
        
         # Cálculos de estadísticas
        solicitudes_pagadas = solicitudes.filter(estado_pago='pagado')
        solicitudes_pendientes = solicitudes.filter(estado_pago='pendiente', estado='aceptada')
        
        total_gastado = sum(float(s.monto_final or s.monto_acordado) for s in solicitudes_pagadas if s.monto_acordado)
        total_pendiente = sum(float(s.monto_acordado) for s in solicitudes_pendientes if s.monto_acordado)
        
        # Gastos por mes para el gráfico
        gastos_por_mes = []
        meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                        'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        for mes_num in range(1, 13):
            gastos_mes = solicitudes_pagadas.filter(
                fecha_solicitud__month=mes_num,
                fecha_solicitud__year=año
            )
            total_mes = sum(float(s.monto_final or s.monto_acordado) for s in gastos_mes if s.monto_acordado)
            gastos_por_mes.append(round(total_mes, 2))
        
        # Años disponibles
        años_disponibles = list(set([
            s.fecha_solicitud.year for s in SolicitudClase.objects.filter(alumno=alumno)
            if s.fecha_solicitud
        ]))
        if not años_disponibles:
            años_disponibles = [timezone.now().year]
        else:
            años_disponibles.sort(reverse=True)
        
        # Gastos por maestro
        gastos_por_maestro = {}
        for solicitud in solicitudes_pagadas:
            if solicitud.monto_acordado:
                maestro_nombre = solicitud.maestro.usuario.get_full_name()
                monto = float(solicitud.monto_acordado)
                
                if maestro_nombre in gastos_por_maestro:
                    gastos_por_maestro[maestro_nombre]['monto'] += monto
                    gastos_por_maestro[maestro_nombre]['clases'] += 1
                else:
                    gastos_por_maestro[maestro_nombre] = {
                        'monto': monto,
                        'clases': 1,
                        'maestro_id': solicitud.maestro.id,
                    }
        
        # Gastos por materia
        gastos_por_materia = {}
        for solicitud in solicitudes_pagadas:
            if solicitud.monto_acordado:
                materia_nombre = solicitud.materia.nombre
                monto = float(solicitud.monto_acordado)
                
                if materia_nombre in gastos_por_materia:
                    gastos_por_materia[materia_nombre] += monto
                else:
                    gastos_por_materia[materia_nombre] = monto
        
        # Próximos pagos pendientes
        ahora = timezone.now()
        proximos_pagos = solicitudes.filter(
            estado_pago='pendiente', 
            estado='aceptada'
        ).order_by('fecha_clase_confirmada')
        
        # Historial de pagos
        historial_pagos = solicitudes_pagadas.order_by('-fecha_pago')[:10]
        
        context = {
            'solicitudes': solicitudes,
            'total_gastado': total_gastado,
            'total_pendiente': total_pendiente,

            """ 'total_clases': total_clases, """

            'gastos_por_mes': gastos_por_mes,
            'meses_nombres': meses_nombres,
            'años_disponibles': años_disponibles,
            'mes_filtro': mes,
            'año_filtro': año,
            'gastos_por_maestro': gastos_por_maestro,
            'gastos_por_materia': gastos_por_materia,
            'proximos_pagos': proximos_pagos,
            'historial_pagos': historial_pagos,
            
            'solicitudes_pagadas': solicitudes_pagadas,
            'solicitudes_pendientes': solicitudes_pendientes,
            'debug_info': {
                'total_solicitudes': solicitudes.count(),
                'pagadas_count': solicitudes_pagadas.count(),
                'pendientes_count': solicitudes_pendientes.count(),
            }
        }
        
        return render(request, 'alumno/control_gastos.html', context)
        
    except Alumno.DoesNotExist:
        messages.error(request, "No tienes un perfil de alumno.")
        return redirect('dashboard_alumno')
    except Exception as e:
        messages.error(request, f"Error en control de gastos: {str(e)}")
        return redirect('dashboard_alumno')


@login_required
def exportar_gastos_pdf(request):
    """Exportar gastos a PDF"""
    try:
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib import colors
        
        alumno = Alumno.objects.get(usuario=request.user)
        
        # Obtener parámetros de filtro
        mes = request.GET.get('mes')
        año = request.GET.get('año', timezone.now().year)
        
        # Obtener solicitudes filtradas
        solicitudes = SolicitudClase.objects.filter(
            alumno=alumno
        ).exclude(monto_acordado__isnull=True).select_related(
            'maestro', 'maestro__usuario', 'materia'
        ).order_by('-fecha_solicitud')
        
        if mes and año:
            try:
                solicitudes = solicitudes.filter(
                    fecha_solicitud__year=int(año),
                    fecha_solicitud__month=int(mes)
                )
            except (ValueError, TypeError):
                pass
        
        # Crear PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Título
        title = Paragraph(f"Reporte de Gastos - {alumno.usuario.get_full_name()}", styles['Heading1'])
        elements.append(title)
        
        # Información del período
        periodo_text = f"Período: {mes if mes else 'Todos los meses'} / {año}" if año else "Todos los períodos"
        periodo = Paragraph(periodo_text, styles['Normal'])
        elements.append(periodo)
        
        # Tabla de gastos
        data = [['Fecha', 'Materia', 'Profesor', 'Monto', 'Estado']]
        
        for solicitud in solicitudes:
            data.append([
                solicitud.fecha_solicitud.strftime("%d/%m/%Y"),
                solicitud.materia.nombre,
                solicitud.maestro.usuario.get_full_name(),
                f"${solicitud.monto_final or solicitud.monto_acordado}",
                solicitud.estado_pago
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        
        elements.append(table)
        
        # Generar PDF
        doc.build(elements)
        
        # Preparar respuesta
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="gastos_{alumno.usuario.username}_{año}_{mes or "total"}.pdf"'
        
        return response
        
    except Exception as e:
        messages.error(request, f"Error al generar PDF: {str(e)}")
        return redirect('control_gastos_alumno')


@login_required
def detalle_gastos_maestro(request, maestro_id):
    """Vista detallada de gastos con un maestro específico"""
    try:
        alumno = Alumno.objects.get(usuario=request.user)
        maestro = get_object_or_404(Maestro, id=maestro_id)
        
        # Obtener todas las clases con este maestro
        clases_con_maestro = SolicitudClase.objects.filter(
            alumno=alumno,
            maestro=maestro
        ).exclude(monto_acordado__isnull=True).order_by('-fecha_clase_propuesta')
        
        # Estadísticas específicas
        total_gastado_maestro = sum(c.monto_acordado for c in clases_con_maestro.filter(estado_pago='pagado'))
        total_clases_maestro = clases_con_maestro.count()
        clases_pendientes = clases_con_maestro.filter(estado_pago='pendiente', estado='aceptada')
        
        context = {
            'maestro': maestro,
            'clases_con_maestro': clases_con_maestro,
            'total_gastado_maestro': total_gastado_maestro,
            'total_clases_maestro': total_clases_maestro,
            'clases_pendientes': clases_pendientes,
        }
        
        return render(request, 'alumno/detalle_gastos_maestro.html', context)
        
    except Alumno.DoesNotExist:
        messages.error(request, "No tienes un perfil de alumno.")
        return redirect('dashboard_alumno')
    


@login_required
def marcar_pago_realizado(request, solicitud_id):
    """Vista para que el alumno marque un pago como realizado"""
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id)
    
    # Verificar que el alumno es el dueño de la solicitud
    if solicitud.alumno.usuario != request.user:
        messages.error(request, "No tienes permiso para esta acción.")
        return redirect('mis_solicitudes_alumno')
    
    if request.method == 'POST':
        try:
            solicitud.estado_pago = 'pagado'
            solicitud.fecha_pago = timezone.now()
            solicitud.save()
            
            # Crear notificación para el maestro
            crear_notificacion(
                usuario=solicitud.maestro.usuario,
                tipo='solicitud',
                mensaje=f'El alumno {solicitud.alumno.usuario.get_full_name()} marcó como pagada la clase de {solicitud.materia.nombre}',
                enlace=f'/maestro/solicitudes/'
            )
            
            messages.success(request, '✅ Pago marcado como realizado correctamente.')
            return redirect('control_gastos_alumno')
            
        except Exception as e:
            messages.error(request, f'❌ Error al marcar el pago: {str(e)}')
    
    return render(request, 'alumno/marcar_pago.html', {
        'solicitud': solicitud
    })

@login_required
def confirmar_pago_maestro(request, solicitud_id):
    """Vista para que el maestro confirme la recepción del pago"""
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id)
    
    # Verificar que el maestro es el dueño de la solicitud
    if solicitud.maestro.usuario != request.user:
        messages.error(request, "No tienes permiso para esta acción.")
        return redirect('solicitudes_para_maestro')
    
    if request.method == 'POST':
        try:
            solicitud.estado_pago = 'pagado'
            solicitud.fecha_pago = timezone.now()
            solicitud.save()
            
            # Crear notificación para el alumno
            crear_notificacion(
                usuario=solicitud.alumno.usuario,
                tipo='solicitud',
                mensaje=f'El maestro {solicitud.maestro.usuario.get_full_name()} confirmó el pago de la clase de {solicitud.materia.nombre}',
                enlace=f'/alumno/solicitudes/'
            )
            
            messages.success(request, '✅ Pago confirmado correctamente.')
            return redirect('solicitudes_para_maestro')
            
        except Exception as e:
            messages.error(request, f'❌ Error al confirmar el pago: {str(e)}')
    
    return render(request, 'maestro/confirmar_pago.html', {
        'solicitud': solicitud
    })


@login_required
def corregir_estados_pago(request):
    """Vista temporal para corregir estados de pago de solicitudes existentes"""
    if not request.user.is_superuser:
        messages.error(request, "Solo administradores pueden acceder a esta función.")
        return redirect('home')
    
    try:
        # Obtener todas las solicitudes aceptadas o completadas que no tienen estado_pago definido
        solicitudes = SolicitudClase.objects.filter(
            Q(estado='aceptada') | Q(estado='completada')
        ).filter(
            Q(estado_pago__isnull=True) | Q(estado_pago='')
        )
        
        correcciones = 0
        for solicitud in solicitudes:
            # Si tiene monto_acordado, asumimos que el pago está pendiente
            if solicitud.monto_acordado:
                solicitud.estado_pago = 'pendiente'
                solicitud.save()
                correcciones += 1
                print(f"✅ Corregida: {solicitud.id} - {solicitud.materia.nombre} - ${solicitud.monto_acordado}")
        
        messages.success(request, f"Se corrigieron {correcciones} solicitudes.")
        
    except Exception as e:
        messages.error(request, f"Error al corregir: {str(e)}")
    
    return redirect('home')



# ===== HERRAMIENTAS INTEGRADAS =====

@login_required
def herramientas(request):
    """Vista principal del kit de herramientas con estadísticas reales"""
    # Obtener estadísticas REALES del usuario
    tareas_usuario = Tarea.objects.filter(usuario=request.user)
    total_tareas = tareas_usuario.count()
    tareas_pendientes = tareas_usuario.filter(completada=False).count()
    tareas_completadas = tareas_usuario.filter(completada=True).count()
    
    sesiones_usuario = SesionEstudio.objects.filter(usuario=request.user)
    total_sesiones = sesiones_usuario.count()
    
    # Tareas próximas a vencer (próximos 2 días)
    hoy = timezone.now()
    proximas_48_horas = hoy + timedelta(days=2)
    tareas_proximas = tareas_usuario.filter(
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=proximas_48_horas,
        completada=False
    ).count()
    
    # Minutos estudiados hoy
    hoy_inicio = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
    minutos_hoy = sesiones_usuario.filter(
        fecha_inicio__gte=hoy_inicio
    ).aggregate(Sum('duracion_minutos'))['duracion_minutos__sum'] or 0

    context = {
        'total_tareas': total_tareas,
        'tareas_pendientes': tareas_pendientes,
        'tareas_completadas': tareas_completadas,
        'tareas_proximas': tareas_proximas,
        'total_sesiones': total_sesiones,
        'minutos_hoy': minutos_hoy,
    }
    return render(request, 'herramientas/herramientas.html', context)

# CALCULADORA
@login_required
def calculadora(request):
    return render(request, 'herramientas/calculadora.html')

# BLOC DE NOTAS
@login_required
def bloc_notas(request):
    """Vista mejorada del bloc de notas con múltiples hojas"""
    # Obtener o crear el bloc de notas del usuario
    bloc, created = BlocNotas.objects.get_or_create(usuario=request.user)
    
    # Obtener todas las notas del usuario
    notas = bloc.notas.all()
    
    # Manejar creación de nueva nota
    if request.method == 'POST' and 'crear_nota' in request.POST:
        nueva_nota = Nota.objects.create(
            bloc_notas=bloc,
            titulo="Nueva nota",
            contenido=""
        )
        return redirect('editar_nota', nota_id=nueva_nota.id)
    
    # Manejar guardado desde la lista
    if request.method == 'POST' and 'guardar_todo' in request.POST:
        for nota in notas:
            contenido_key = f"contenido_{nota.id}"
            if contenido_key in request.POST:
                nota.contenido = request.POST[contenido_key]
                nota.save()
        messages.success(request, "Todas las notas guardadas correctamente.")
        return redirect('bloc_notas')
    
    return render(request, 'herramientas/bloc_notas.html', {
        'bloc': bloc,
        'notas': notas,
        'form': NotaForm()  # Para crear nuevas notas
    })

@login_required
def editar_nota(request, nota_id):
    """Vista para editar una nota específica"""
    nota = get_object_or_404(Nota, id=nota_id, bloc_notas__usuario=request.user)
    
    if request.method == 'POST':
        form = NotaForm(request.POST, instance=nota)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nota guardada correctamente.')
            return redirect('bloc_notas')
    else:
        form = NotaForm(instance=nota)
    
    # Obtener todas las notas para mostrar en el sidebar
    todas_las_notas = nota.bloc_notas.notas.all()
    
    return render(request, 'herramientas/editar_nota.html', {
        'form': form,
        'nota': nota,
        'todas_las_notas': todas_las_notas
    })


@login_required
def crear_nota(request):
    """Crear una nueva nota"""
    bloc, created = BlocNotas.objects.get_or_create(usuario=request.user)
    
    if request.method == 'POST':
        form = NotaForm(request.POST)
        if form.is_valid():
            nueva_nota = form.save(commit=False)
            nueva_nota.bloc_notas = bloc
            nueva_nota.save()
            messages.success(request, 'Nota creada correctamente.')
            return redirect('editar_nota', nota_id=nueva_nota.id)
    else:
        form = NotaForm(initial={'titulo': 'Nueva nota'})
    
    return render(request, 'herramientas/crear_nota.html', {'form': form})


@login_required
def eliminar_nota(request, nota_id):
    """Eliminar una nota"""
    nota = get_object_or_404(Nota, id=nota_id, bloc_notas__usuario=request.user)
    
    if request.method == 'POST':
        nota.delete()
        messages.success(request, 'Nota eliminada correctamente.')
        return redirect('bloc_notas')
    
    return render(request, 'herramientas/eliminar_nota.html', {'nota': nota})

# GESTOR DE TAREAS
@login_required
def gestor_tareas(request):
    tareas = Tarea.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    
    if request.method == 'POST':
        form = TareaForm(request.POST)
        if form.is_valid():
            try:
                tarea = form.save(commit=False)
                tarea.usuario = request.user
                tarea.estado = 'pendiente'  # ✅ ESTABLECER ESTADO POR DEFECTO
                tarea.completada = False    # ✅ ESTABLECER COMPLETADA POR DEFECTO
                tarea.save()
                
                # Para peticiones AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success', 
                        'tarea_id': tarea.id,
                        'message': 'Tarea creada correctamente'
                    })
                
                messages.success(request, 'Tarea creada correctamente.')
                return redirect('gestor_tareas')
                
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Error al guardar: {str(e)}'
                    }, status=400)
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            # Si el formulario tiene errores
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'errors': form.errors
                }, status=400)
    
    # Para GET requests
    form = TareaForm()
    
    # Marcar tareas próximas a vencer
    hoy = timezone.now()
    for tarea in tareas:
        if tarea.fecha_vencimiento:
            diferencia = tarea.fecha_vencimiento - hoy
            tarea.esta_proxima = diferencia.days <= 2 and diferencia.days >= 0
    
    # Estadísticas
    total_tareas = tareas.count()
    tareas_pendientes = tareas.filter(completada=False).count()
    tareas_completadas = tareas.filter(completada=True).count()
    
    context = {
        'tareas': tareas,
        'form': form,
        'total_tareas': total_tareas,
        'tareas_pendientes': tareas_pendientes,
        'tareas_completadas': tareas_completadas,
    }
    
    return render(request, 'herramientas/gestor_tareas.html', context)

@login_required
def cambiar_estado_tarea(request, tarea_id):
    """Cambiar estado de tarea via AJAX - CORREGIDA"""
    tarea = get_object_or_404(Tarea, id=tarea_id, usuario=request.user)
    
    if request.method == 'POST':
        try:
            completada = request.POST.get('completada') == 'true'
            tarea.completada = completada
            
            if completada:
                tarea.estado = 'completada'
                tarea.fecha_completada = timezone.now()
            else:
                tarea.estado = 'pendiente'
                tarea.fecha_completada = None
            
            tarea.save()
            
            return JsonResponse({
                'status': 'success', 
                'nuevo_estado': tarea.estado,
                'completada': tarea.completada
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

@login_required
def eliminar_tarea(request, tarea_id):
    """Eliminar tarea via AJAX"""
    tarea = get_object_or_404(Tarea, id=tarea_id, usuario=request.user)
    
    if request.method == 'POST':
        try:
            tarea.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

# POMODORO TIMER
@login_required
def pomodoro_timer(request):
    if request.method == 'POST':
        form = SesionEstudioForm(request.POST)
        if form.is_valid():
            sesion = form.save(commit=False)
            sesion.usuario = request.user
            sesion.save()
            return JsonResponse({'status': 'success', 'sesion_id': sesion.id})
    
    # Obtener estadísticas de estudio
    sesiones_hoy = SesionEstudio.objects.filter(
        usuario=request.user,
        fecha_inicio__date=timezone.now().date()
    )
    total_minutos_hoy = sum(s.duracion_minutos for s in sesiones_hoy)
    
    context = {
        'total_minutos_hoy': total_minutos_hoy,
        'sesiones_hoy': sesiones_hoy.count(),
    }
    
    return render(request, 'herramientas/pomodoro_timer.html', context)

@login_required
def finalizar_sesion_estudio(request):
    """Finalizar sesión de estudio via AJAX"""
    if request.method == 'POST':
        sesion_id = request.POST.get('sesion_id')
        duracion = request.POST.get('duracion')
        
        try:
            sesion = SesionEstudio.objects.get(id=sesion_id, usuario=request.user)
            sesion.fecha_fin = timezone.now()
            sesion.duracion_minutos = int(duracion)
            sesion.save()
            return JsonResponse({'status': 'success'})
        except SesionEstudio.DoesNotExist:
            return JsonResponse({'status': 'error'})
    
    return JsonResponse({'status': 'error'})

# CONVERSOR DE UNIDADES
@login_required
def conversor_unidades(request):
    return render(request, 'herramientas/conversor_unidades.html')

# GENERADOR DE GRÁFICOS
@login_required
def generador_graficos(request):
    return render(request, 'herramientas/generador_graficos.html')




# ===== NUEVAS HERRAMIENTAS =====
from django.http import JsonResponse
import json
import requests

# Biblioteca de fórmulas matemáticas
@login_required
def biblioteca_formulas(request):
    """Biblioteca de fórmulas matemáticas organizadas por categoría"""
    # Datos de fórmulas (puedes expandir esto)
    formulas_por_categoria = {
        'Álgebra': [
            {'nombre': 'Ecuación cuadrática', 'formula': 'x = [-b ± √(b² - 4ac)] / 2a'},
            {'nombre': 'Teorema de Pitágoras', 'formula': 'a² + b² = c²'},
            {'nombre': 'Logaritmos', 'formula': 'logₐ(b) = c ⇔ aᶜ = b'},
        ],
        'Cálculo': [
            {'nombre': 'Derivada básica', 'formula': 'd/dx(xⁿ) = n·xⁿ⁻¹'},
            {'nombre': 'Regla de la cadena', 'formula': 'd/dx[f(g(x))] = f\'(g(x))·g\'(x)'},
            {'nombre': 'Integral definida', 'formula': '∫ₐᵇ f(x) dx = F(b) - F(a)'},
        ],
        'Geometría': [
            {'nombre': 'Área del círculo', 'formula': 'A = π·r²'},
            {'nombre': 'Volumen de la esfera', 'formula': 'V = (4/3)π·r³'},
            {'nombre': 'Teorema del coseno', 'formula': 'c² = a² + b² - 2ab·cos(C)'},
        ],
        'Estadística': [
            {'nombre': 'Media aritmética', 'formula': 'x̄ = (Σxᵢ) / n'},
            {'nombre': 'Desviación estándar', 'formula': 'σ = √[Σ(xᵢ - x̄)² / n]'},
            {'nombre': 'Distribución normal', 'formula': 'f(x) = (1/σ√(2π))·e^(-(x-μ)²/2σ²)'},
        ],
        'Física': [
            {'nombre': 'Segunda ley de Newton', 'formula': 'F = m·a'},
            {'nombre': 'Energía cinética', 'formula': 'E = ½·m·v²'},
            {'nombre': 'Ley de Ohm', 'formula': 'V = I·R'},
        ]
    }
    
    return render(request, 'herramientas/biblioteca_formulas.html', {
        'formulas_por_categoria': formulas_por_categoria,
    })

# Tabla periódica interactiva
@login_required
def tabla_periodica(request):
    """Tabla periódica interactiva con información de elementos"""
    # Datos de elementos químicos (simplificado)
    elementos = [
        {'simbolo': 'H', 'nombre': 'Hidrógeno', 'numero': 1, 'masa': 1.008, 'grupo': 1},
        {'simbolo': 'He', 'nombre': 'Helio', 'numero': 2, 'masa': 4.0026, 'grupo': 18},
        {'simbolo': 'Li', 'nombre': 'Litio', 'numero': 3, 'masa': 6.94, 'grupo': 1},
        {'simbolo': 'Be', 'nombre': 'Berilio', 'numero': 4, 'masa': 9.0122, 'grupo': 2},
        {'simbolo': 'B', 'nombre': 'Boro', 'numero': 5, 'masa': 10.81, 'grupo': 13},
        # Agregar más elementos según necesites
    ]
    
    # Grupos por color
    grupos_colores = {
        1: '#FF9999',    # Alcalinos
        2: '#FFDEAD',    # Alcalinotérreos
        13: '#FFB366',   # Grupo del Boro
        14: '#CCCC99',   # Grupo del Carbono
        15: '#99CC99',   # Nitrogenoides
        16: '#99CCCC',   # Calcógenos
        17: '#9999CC',   # Halógenos
        18: '#CC99CC',   # Gases nobles
    }
    
    return render(request, 'herramientas/tabla_periodica.html', {
        'elementos': elementos,
        'grupos_colores': grupos_colores,
    })

# Traductor automático (usando API gratuita)
@login_required
def traductor_automatico(request):
    """Traductor automático usando API de MyMemory"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        texto = request.POST.get('texto', '')
        idioma_origen = request.POST.get('idioma_origen', 'es')
        idioma_destino = request.POST.get('idioma_destino', 'en')
        
        try:
            # Usar API de MyMemory (gratuita con límites)
            url = "https://api.mymemory.translated.net/get"
            params = {
                'q': texto,
                'langpair': f'{idioma_origen}|{idioma_destino}'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            traduccion = data['responseData']['translatedText']
            return JsonResponse({'success': True, 'traduccion': traduccion})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # Lista de idiomas soportados
    idiomas = [
        {'codigo': 'es', 'nombre': 'Español'},
        {'codigo': 'en', 'nombre': 'Inglés'},
        {'codigo': 'fr', 'nombre': 'Francés'},
        {'codigo': 'de', 'nombre': 'Alemán'},
        {'codigo': 'it', 'nombre': 'Italiano'},
        {'codigo': 'pt', 'nombre': 'Portugués'},
        {'codigo': 'ru', 'nombre': 'Ruso'},
        {'codigo': 'zh', 'nombre': 'Chino'},
        {'codigo': 'ja', 'nombre': 'Japonés'},
        {'codigo': 'ko', 'nombre': 'Coreano'},
    ]
    
    return render(request, 'herramientas/traductor_automatico.html', {
        'idiomas': idiomas,
    })

# Diccionario integrado (usando API de DictionaryAPI)
@login_required
def diccionario_integrado(request):
    """Diccionario de español/inglés"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        palabra = request.POST.get('palabra', '').strip().lower()
        idioma = request.POST.get('idioma', 'es')
        
        try:
            if idioma == 'es':
                # Para español, usar API de RAE (alternativa)
                url = f"https://dle.rae.es/data/{palabra}"
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    definiciones = []
                    
                    for resultado in data.get('res', []):
                        for acepcion in resultado.get('acept', []):
                            definiciones.append(acepcion.get('def', ''))
                    
                    return JsonResponse({
                        'success': True,
                        'palabra': palabra,
                        'definiciones': definiciones[:5],  # Limitar a 5 definiciones
                        'fuente': 'RAE'
                    })
                else:
                    # Fallback a API de WordReference
                    url = f"https://api.wordreference.com/0.8/80143/json/esen/{palabra}"
                    response = requests.get(url)
                    data = response.json()
                    
                    definiciones = []
                    if 'term0' in data:
                        for entry in data['term0']['PrincipalTranslations']:
                            definiciones.append(entry['FirstTranslation']['term'])
                    
                    return JsonResponse({
                        'success': True,
                        'palabra': palabra,
                        'definiciones': definiciones[:5],
                        'fuente': 'WordReference'
                    })
                    
            elif idioma == 'en':
                # Para inglés, usar Free Dictionary API
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{palabra}"
                response = requests.get(url)
                data = response.json()
                
                definiciones = []
                if isinstance(data, list):
                    for entry in data:
                        for meaning in entry.get('meanings', []):
                            for definition in meaning.get('definitions', []):
                                definiciones.append(definition.get('definition', ''))
                
                return JsonResponse({
                    'success': True,
                    'palabra': palabra,
                    'definiciones': definiciones[:5],
                    'fuente': 'Free Dictionary API'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'sugerencia': 'Intenta con otra palabra o verifica la conexión a internet.'
            })
    
    return render(request, 'herramientas/diccionario_integrado.html')

# Sinónimos y antónimos
@login_required
def sinonimos_antonimos(request):
    """Buscador de sinónimos y antónimos"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        palabra = request.POST.get('palabra', '').strip().lower()
        tipo = request.POST.get('tipo', 'sinonimos')  # 'sinonimos' o 'antonimos'
        
        try:
            # Usar Datamuse API para sinónimos/antónimos en inglés
            if tipo == 'sinonimos':
                url = f"https://api.datamuse.com/words?rel_syn={palabra}&max=10"
            else:
                url = f"https://api.datamuse.com/words?rel_ant={palabra}&max=10"
            
            response = requests.get(url)
            palabras_relacionadas = response.json()
            
            resultados = [item['word'] for item in palabras_relacionadas[:8]]
            
            return JsonResponse({
                'success': True,
                'palabra': palabra,
                'tipo': tipo,
                'resultados': resultados
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return render(request, 'herramientas/sinonimos_antonimos.html')




@login_required
def ingresos_detallados(request):
    """Vista detallada de ingresos del maestro - TODOS LOS CÁLCULOS EN VISTA (fusionado con filtros de año/mes)"""
    try:
        perfil_maestro = Maestro.objects.get(usuario=request.user)
    except Maestro.DoesNotExist:
        messages.error(request, "No tienes un perfil de maestro.")
        return redirect("dashboard_maestro")
    
    # ======== Fechas base ========
    ahora = timezone.now()
    mes_actual = ahora.month
    año_actual = ahora.year

    # ======== Obtener todas las clases pagadas ========
    clases_pagadas = SolicitudClase.objects.filter(
        maestro=perfil_maestro,
        estado_pago='pagado'
    ).select_related('alumno', 'alumno__usuario', 'materia').order_by('-fecha_pago')

    # ======================================================
    #   FUSIÓN DEL SISTEMA DE FILTROS:
    #   - Tus filtros: actual / anterior / año
    #   - Filtros del código nuevo: mes & año manuales
    # ======================================================

    filtro_mes = request.GET.get('mes', None)        # Puede ser: "actual", "anterior", "5", "8", etc.
    filtro_año = request.GET.get('año', año_actual) # Puede ser numérico

    try:
        filtro_año = int(filtro_año)
    except (ValueError, TypeError):
        filtro_año = año_actual

    clases_filtradas = clases_pagadas
    mes_nombre = ""

    # ===============================
    #   PARTES DEL CÓDIGO NUEVO
    #   Si mes es un número → usar filtro tradicional
    # ===============================
    if filtro_mes and filtro_mes.isdigit():
        try:
            mes_int = int(filtro_mes)
            clases_filtradas = clases_pagadas.filter(
                fecha_pago__year=filtro_año,
                fecha_pago__month=mes_int
            )
            mes_nombre = f"{mes_int}/{filtro_año}"
        except:
            pass

    else:
        # ===============================
        #   TU SISTEMA DE FILTROS ORIGINAL
        # ===============================

        if filtro_mes == 'actual':
            clases_filtradas = clases_pagadas.filter(
                fecha_pago__month=mes_actual,
                fecha_pago__year=año_actual
            )
            mes_nombre = ahora.strftime("%B %Y")

        elif filtro_mes == 'anterior':
            if mes_actual == 1:
                mes_anterior = 12
                año_anterior = año_actual - 1
            else:
                mes_anterior = mes_actual - 1
                año_anterior = año_actual
            
            clases_filtradas = clases_pagadas.filter(
                fecha_pago__month=mes_anterior,
                fecha_pago__year=año_anterior
            )
            fecha_anterior = ahora.replace(month=mes_anterior, year=año_anterior)
            mes_nombre = fecha_anterior.strftime("%B %Y")

        else:
            clases_filtradas = clases_pagadas.filter(
                fecha_pago__year=filtro_año
            )
            mes_nombre = f"Año {filtro_año}"

    # ======================================================
    #   CALCULAR TODO EN LA VISTA - NO EN EL TEMPLATE
    # ======================================================

    # 1. Total de ingresos y clases
    total_ingresos = 0
    total_clases = clases_filtradas.count()
    
    for clase in clases_filtradas:
        if clase.monto_acordado:
            total_ingresos += float(clase.monto_acordado)

    # 2. Promedio por clase
    promedio_por_clase = total_ingresos / total_clases if total_clases > 0 else 0

    # 3. Ingresos por materia
    ingresos_por_materia = {}
    for clase in clases_filtradas:
        if clase.monto_acordado:
            materia = clase.materia.nombre
            monto = float(clase.monto_acordado)
            ingresos_por_materia[materia] = ingresos_por_materia.get(materia, 0) + monto

    materias_con_datos = [
        {
            'nombre': materia,
            'monto': round(monto, 2),
            'porcentaje': round((monto / total_ingresos * 100), 1) if total_ingresos > 0 else 0
        }
        for materia, monto in ingresos_por_materia.items()
    ]
    materias_con_datos.sort(key=lambda x: x['monto'], reverse=True)

    # 4. Ingresos por alumno
    ingresos_por_alumno = {}
    for clase in clases_filtradas:
        if clase.monto_acordado:
            alumno_nombre = clase.alumno.usuario.get_full_name() or clase.alumno.usuario.username
            monto = float(clase.monto_acordado)
            if alumno_nombre not in ingresos_por_alumno:
                ingresos_por_alumno[alumno_nombre] = {
                    'monto': 0,
                    'clases': 0,
                    'alumno_id': clase.alumno.id
                }
            ingresos_por_alumno[alumno_nombre]['monto'] += monto
            ingresos_por_alumno[alumno_nombre]['clases'] += 1

    alumnos_con_datos = [
        {
            'nombre': nombre,
            'monto': round(datos['monto'], 2),
            'clases': datos['clases'],
            'alumno_id': datos['alumno_id']
        }
        for nombre, datos in ingresos_por_alumno.items()
    ]
    alumnos_con_datos.sort(key=lambda x: x['monto'], reverse=True)

    # 5. Ingresos mensuales (como el código nuevo)
    ingresos_mensuales = []
    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                     'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    for mes in range(1, 13):
        ingresos_mes = sum(
            float(clase.monto_acordado)
            for clase in clases_pagadas.filter(fecha_pago__month=mes, fecha_pago__year=filtro_año)
            if clase.monto_acordado
        )
        ingresos_mensuales.append(round(ingresos_mes, 2))

    # 6. Años disponibles
    años_disponibles = list(set([
        clase.fecha_pago.year for clase in clases_pagadas if clase.fecha_pago
    ]))
    años_disponibles = sorted(años_disponibles, reverse=True) or [año_actual]

    # 7. Métodos de pago
    metodos_pago = {}
    for clase in clases_filtradas:
        metodo = clase.get_metodo_pago_display()
        metodos_pago[metodo] = metodos_pago.get(metodo, 0) + 1

    # ===== CONTEXTO FINAL =====
    context = {
        'clases_pagadas': clases_filtradas,
        'total_ingresos': round(total_ingresos, 2),
        'total_clases': total_clases,
        'promedio_por_clase': round(promedio_por_clase, 2),
        'materias_con_datos': materias_con_datos,
        'alumnos_con_datos': alumnos_con_datos[:5],  # top 5
        'ingresos_mensuales': ingresos_mensuales,
        'meses_nombres': meses_nombres,
        'mes_nombre': mes_nombre,
        'filtro_mes': filtro_mes,
        'filtro_año': filtro_año,
        'años_disponibles': años_disponibles,
        'metodos_pago': metodos_pago,
        'año_actual': año_actual,
    }
    
    return render(request, 'maestro/ingresos_detallados.html', context)




@login_required
def editar_perfil_alumno(request):
    """Vista para que el alumno edite su propio perfil"""
    try:
        alumno = Alumno.objects.get(usuario=request.user)
    except Alumno.DoesNotExist:
        messages.error(request, "No tienes un perfil de alumno.")
        return redirect("dashboard_alumno")

    if request.method == "POST":
        usuario_form = UsuarioForm(request.POST, request.FILES, instance=request.user)
        alumno_form = AlumnoForm(request.POST, instance=alumno)

        if usuario_form.is_valid() and alumno_form.is_valid():
            usuario_form.save()
            alumno_form.save()
            messages.success(request, "¡Perfil actualizado correctamente!")
            return redirect("dashboard_alumno")
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        usuario_form = UsuarioForm(instance=request.user)
        alumno_form = AlumnoForm(instance=alumno)

    return render(
        request,
        "alumno/perfil_alumno.html",
        {"usuario_form": usuario_form, "alumno_form": alumno_form},
    )




def admin_required(function=None):
    """Decorator para verificar si el usuario es administrador"""
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Debes iniciar sesión para acceder al panel de administración.")
                return redirect('login')
            
            # Verificar si es superusuario o tiene rol ADMIN
            if not (request.user.is_superuser or getattr(request.user, 'rol', None) == 'ADMIN'):
                messages.error(request, "No tienes permisos para acceder al panel de administración.")
                return redirect('home')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view

    if function:
        return decorator(function)
    return decorator


# MUEVE el decorador admin_required ANTES de las vistas que lo usan
@admin_required
def dashboard_admin(request):
    """Dashboard principal del administrador"""
    try:
        # Estadísticas generales
        total_usuarios = Usuario.objects.count()
        total_alumnos = Alumno.objects.count()
        total_maestros = Maestro.objects.count()
        total_clases = SolicitudClase.objects.count()
        
        # Clases por estado
        clases_por_estado = SolicitudClase.objects.values('estado').annotate(
            total=Count('id')
        ).order_by('-total')
        
        # Ingresos totales
        ingresos_totales = SolicitudClase.objects.filter(
            estado_pago='pagado'
        ).aggregate(Sum('monto_final'))['monto_final__sum'] or 0
        
        # Usuarios nuevos este mes
        from datetime import datetime
        primer_dia_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        nuevos_usuarios_mes = Usuario.objects.filter(
            fecha_creacion__gte=primer_dia_mes
        ).count()
        
        # Materias más populares
        from catalogo.models import Materia
        materias_populares = Materia.objects.annotate(
            total_clases=Count('solicitudclase'),
            total_maestros=Count('maestros')
        ).order_by('-total_clases')[:10]
        
        context = {
            'total_usuarios': total_usuarios,
            'total_alumnos': total_alumnos,
            'total_maestros': total_maestros,
            'total_clases': total_clases,
            'clases_por_estado': clases_por_estado,
            'ingresos_totales': ingresos_totales,
            'nuevos_usuarios_mes': nuevos_usuarios_mes,
            'materias_populares': materias_populares,
        }
        
        return render(request, 'admin/dashboard_admin.html', context)
    
    except Exception as e:
        messages.error(request, f"Error al cargar el dashboard: {str(e)}")
        return redirect('home')    



@admin_required
def estadisticas_detalladas(request):
    """Estadísticas detalladas del sistema"""
    # Aquí va el código completo de estadisticas_detalladas que te pasé antes
    # ... (usa el código completo que te proporcioné en la respuesta anterior)


@admin_required
def gestion_promociones(request):
    """Gestión de promociones"""
    promociones = Promocion.objects.all().order_by('-fecha_inicio')
    
    if request.method == 'POST':
        form = PromocionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Promoción creada correctamente.')
            return redirect('gestion_promociones')
    else:
        form = PromocionForm()
    
    return render(request, 'admin/gestion_promociones.html', {
        'promociones': promociones,
        'form': form
    })


@admin_required
def gestion_vouchers(request):
    """Gestión de vouchers"""
    vouchers = Voucher.objects.all().order_by('-fecha_creacion')
    
    if request.method == 'POST':
        form = VoucherForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Voucher creado correctamente.')
            return redirect('gestion_vouchers')
    else:
        form = VoucherForm()
    
    return render(request, 'admin/gestion_vouchers.html', {
        'vouchers': vouchers,
        'form': form
    })


@login_required
def aplicar_promocion(request):
    return render(request, "admin/aplicar_promocion.html")


def admin_required(function=None):
    """Decorator para verificar si el usuario es administrador"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (u.is_superuser or u.rol == 'ADMIN'),
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


