from django.core.management.base import BaseCommand
from cuentas.models import SolicitudClase
from django.db.models import Q

class Command(BaseCommand):
    help = 'Corrige los estados de pago de las solicitudes existentes'

    def handle(self, *args, **options):
        # Obtener solicitudes que necesitan corrección
        solicitudes = SolicitudClase.objects.filter(
            Q(estado='aceptada') | Q(estado='completada')
        ).filter(
            Q(estado_pago__isnull=True) | Q(estado_pago='')
        )
        
        self.stdout.write(f"Encontradas {solicitudes.count()} solicitudes para corregir")
        
        for solicitud in solicitudes:
            if solicitud.monto_acordado:
                solicitud.estado_pago = 'pendiente'
                solicitud.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Corregida: {solicitud.id} - {solicitud.materia.nombre} - ${solicitud.monto_acordado}"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Se corrigieron {solicitudes.count()} solicitudes')
        )