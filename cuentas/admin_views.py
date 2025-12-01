from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import *
from .models import Materia
from .forms import PromocionForm, VoucherForm

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.rol == 'ADMIN')

@login_required
@user_passes_test(is_admin)
def dashboard_admin(request):
    # Estadísticas generales
    total_usuarios = Usuario.objects.count()
    total_alumnos = Alumno.objects.count()
    total_maestros = Maestro.objects.count()
    total_clases = SolicitudClase.objects.count()
    total_instituciones = Institucion.objects.count()
    
    # Clases por estado
    clases_por_estado = SolicitudClase.objects.values('estado').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Ingresos totales
    ingresos_totales = SolicitudClase.objects.filter(
        estado_pago='pagado'
    ).aggregate(Sum('monto_final'))['monto_final__sum'] or 0
    
    # Materias más populares
    materias_populares = Materia.objects.annotate(
        total_clases=Count('solicitudclase'),
        total_maestros=Count('maestros')
    ).order_by('-total_clases')[:10]
    
    # Crecimiento mensual
    hoy = timezone.now()
    primer_dia_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    nuevos_usuarios_mes = Usuario.objects.filter(
        fecha_creacion__gte=primer_dia_mes
    ).count()
    
    nuevas_clases_mes = SolicitudClase.objects.filter(
        fecha_solicitud__gte=primer_dia_mes
    ).count()
    
    # Instituciones con más alumnos
    instituciones_alumnos = Institucion.objects.annotate(
        total_alumnos=Count('usuario', filter=Q(usuario__alumno__isnull=False)),
        total_maestros=Count('usuario', filter=Q(usuario__maestro__isnull=False))
    ).order_by('-total_alumnos')[:10]
    
    context = {
        'total_usuarios': total_usuarios,
        'total_alumnos': total_alumnos,
        'total_maestros': total_maestros,
        'total_clases': total_clases,
        'total_instituciones': total_instituciones,
        'clases_por_estado': clases_por_estado,
        'ingresos_totales': ingresos_totales,
        'materias_populares': materias_populares,
        'nuevos_usuarios_mes': nuevos_usuarios_mes,
        'nuevas_clases_mes': nuevas_clases_mes,
        'instituciones_alumnos': instituciones_alumnos,
    }
    
    return render(request, 'admin/dashboard_admin.html', context)

@login_required
@user_passes_test(is_admin)
def estadisticas_detalladas(request):
    # Filtros
    periodo = request.GET.get('periodo', 'mes')
    materia_id = request.GET.get('materia')
    institucion_id = request.GET.get('institucion')
    
    # Definir rango de fechas según periodo
    hoy = timezone.now()
    if periodo == 'semana':
        fecha_inicio = hoy - timedelta(days=7)
    elif periodo == 'mes':
        fecha_inicio = hoy - timedelta(days=30)
    elif periodo == 'trimestre':
        fecha_inicio = hoy - timedelta(days=90)
    else:
        fecha_inicio = hoy - timedelta(days=30)
    
    # Consultas base
    clases_query = SolicitudClase.objects.filter(fecha_solicitud__gte=fecha_inicio)
    usuarios_query = Usuario.objects.filter(fecha_creacion__gte=fecha_inicio)
    
    # Aplicar filtros
    if materia_id:
        clases_query = clases_query.filter(materia_id=materia_id)
    
    if institucion_id:
        usuarios_query = usuarios_query.filter(institucion_id=institucion_id)
        clases_query = clases_query.filter(
            Q(alumno__usuario__institucion_id=institucion_id) |
            Q(maestro__usuario__institucion_id=institucion_id)
        )
    
    # Estadísticas por rol
    stats_alumnos = clases_query.filter(alumno__isnull=False).aggregate(
        total=Count('id'),
        ingresos=Sum('monto_final', filter=Q(estado_pago='pagado'))
    )
    
    stats_maestros = clases_query.filter(maestro__isnull=False).aggregate(
        total=Count('id'),
        ingresos=Sum('monto_final', filter=Q(estado_pago='pagado'))
    )
    
    # Materias más solicitadas en el periodo
    materias_top = clases_query.values(
        'materia__nombre'
    ).annotate(
        total=Count('id'),
        ingresos=Sum('monto_final', filter=Q(estado_pago='pagado'))
    ).order_by('-total')[:10]
    
    # Instituciones más activas
    instituciones_top = Institucion.objects.annotate(
        total_clases=Count('usuario__alumno__solicitudclase', 
                          filter=Q(usuario__alumno__solicitudclase__fecha_solicitud__gte=fecha_inicio)),
        total_ingresos=Sum('usuario__alumno__solicitudclase__monto_final',
                          filter=Q(usuario__alumno__solicitudclase__estado_pago='pagado'))
    ).filter(total_clases__gt=0).order_by('-total_clases')[:10]
    
    context = {
        'periodo': periodo,
        'stats_alumnos': stats_alumnos,
        'stats_maestros': stats_maestros,
        'materias_top': materias_top,
        'instituciones_top': instituciones_top,
        'materias': Materia.objects.all(),
        'instituciones': Institucion.objects.all(),
    }
    
    return render(request, 'admin/estadisticas_detalladas.html', context)

@login_required
@user_passes_test(is_admin)
def gestion_promociones(request):
    promociones = Promocion.objects.all().order_by('-fecha_inicio')
    
    if request.method == 'POST':
        form = PromocionForm(request.POST)
        if form.is_valid():
            form.save()
            # Redirigir para evitar reenvío
            return redirect('gestion_promociones')
    else:
        form = PromocionForm()
    
    return render(request, 'admin/gestion_promociones.html', {
        'promociones': promociones,
        'form': form
    })

@login_required
@user_passes_test(is_admin)
def gestion_vouchers(request):
    vouchers = Voucher.objects.all().order_by('-fecha_creacion')
    
    if request.method == 'POST':
        form = VoucherForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('gestion_vouchers')
    else:
        form = VoucherForm()
    
    return render(request, 'admin/gestion_vouchers.html', {
        'vouchers': vouchers,
        'form': form
    })