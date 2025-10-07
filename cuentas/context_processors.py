from .models import Notificacion

def notificaciones_globales(request):
    if request.user.is_authenticated:
        return {
            'notificaciones_globales': Notificacion.objects.filter(
                usuario=request.user, 
                leida=False
            ).order_by('-fecha_creacion')[:5],
            'total_notificaciones': Notificacion.objects.filter(
                usuario=request.user, 
                leida=False
            ).count()
        }
    return {}