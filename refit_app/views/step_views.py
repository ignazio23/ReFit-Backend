from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from django.db import transaction
from datetime import datetime, date
from django.utils import timezone
import logging

from refit_app.models import Pasos
from refit_app.views.task_views import calcular_multiplicador

logger = logging.getLogger(__name__)

# ============================================================================
# STEP VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Vistas API relacionadas con el conteo de pasos diarios.
# --------------------------------------------------------------------------
# Registro y consulta de pasos diarios
# --------------------------------------------------------------------------
class StepUpdateView(APIView):
    """
    Permite consultar y actualizar pasos del día para el usuario autenticado.
    - PATCH: suma pasos y aplica lógica de monedas y multiplicador.
    - GET: retorna pasos actuales, pasos totales y monedas del usuario.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Consulta los pasos del día actual para el usuario autenticado.
        Devuelve pasos actuales, totales y monedas.
        """
        hoy = date.today()
        step_obj = Pasos.objects.filter(fk_usuarios=request.user, fecha=hoy).first()
        pasos = step_obj.pasos if step_obj else 0

        return Response({
            "stepsToday": pasos,
            "totalSteps": request.user.pasos_totales,
            "coins": request.user.monedas_actuales
        }, status=HTTP_200_OK)

    def patch(self, request):
        """
        Actualiza pasos para el usuario autenticado:
        - Si recibe un número (campo 'pasos'): suma pasos del día como antes.
        - Si recibe un array de objetos con 'action', 'steps' y 'date': actualiza múltiples fechas.
        - Al finalizar, actualiza el campo 'last_sync' con la fecha-hora actual.
        """
        from datetime import datetime
        nuevos_pasos = request.data.get("pasos")
        lista_acciones = request.data if isinstance(request.data, list) else None

        with transaction.atomic():
            if lista_acciones:
                for entrada in lista_acciones:
                    action = entrada.get("action")
                    steps = entrada.get("steps")
                    fecha_str = entrada.get("date")

                    try:
                        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    except Exception:
                        return Response({"error": f"Formato inválido de fecha: {fecha_str}"}, status=HTTP_400_BAD_REQUEST)

                    if not isinstance(steps, int) or steps < 0:
                        return Response({"error": f"Pasos inválidos en fecha {fecha_str}"}, status=HTTP_400_BAD_REQUEST)

                    step_obj, _ = Pasos.objects.select_for_update().get_or_create(
                        fk_usuarios=request.user,
                        fecha=fecha,
                        defaults={"pasos": 0}
                    )

                    if action == "add":
                        step_obj.pasos += steps
                    elif action == "replace":
                        step_obj.pasos = steps
                    else:
                        return Response({"error": f"Acción inválida en fecha {fecha_str}"}, status=HTTP_400_BAD_REQUEST)

                    step_obj.save()

                    # Solo si es hoy, se actualizan pasos_totales y monedas
                    if fecha == date.today():
                        multiplicador = calcular_multiplicador(request.user)
                        monedas = int((steps * multiplicador) // 200)
                        if action == "add":
                            request.user.pasos_totales += steps
                            request.user.monedas_actuales += monedas
                        elif action == "replace":
                            # Obtener pasos previos y ajustar
                            prev = Pasos.objects.filter(fk_usuarios=request.user, fecha=fecha).first()
                            prev_pasos = prev.pasos if prev else 0
                            delta = steps - prev_pasos
                            monedas_delta = int((delta * multiplicador) // 200)
                            request.user.pasos_totales += delta
                            request.user.monedas_actuales += monedas_delta

            elif isinstance(nuevos_pasos, int) and nuevos_pasos >= 0:
                hoy = date.today()
                step_obj, _ = Pasos.objects.select_for_update().get_or_create(
                    fk_usuarios=request.user,
                    fecha=hoy,
                    defaults={"pasos": 0}
                )

                step_obj.pasos += nuevos_pasos
                step_obj.save()

                multiplicador = calcular_multiplicador(request.user)
                monedas_adicionales = int((nuevos_pasos * multiplicador) // 200)

                request.user.pasos_totales += nuevos_pasos
                request.user.monedas_actuales += monedas_adicionales

            else:
                return Response({"error": "Formato de entrada inválido."}, status=HTTP_400_BAD_REQUEST)

            # Actualizar campo last_sync
            request.user.last_sync = timezone.now()
            request.user.save()

        logger.info("%s actualizó sus pasos. Última sincronización: %s", request.user.email, request.user.last_sync)

        return Response({
            "message": "Pasos actualizados correctamente.",
            "lastSync": request.user.last_sync.strftime("%Y-%m-%d %H:%M:%S")
        }, status=HTTP_200_OK)

# ----------------------------------------------------------------
    """ PATCH VIEJO
    def patch(self, request):
        ""
        Suma pasos del día para el usuario autenticado, aplicando multiplicador si corresponde.
        Reemplaza las views previas: StepCountView y AddStepsView.
        ""
        nuevos_pasos = request.data.get("pasos")

        if not isinstance(nuevos_pasos, int):
            try:
                nuevos_pasos = int(nuevos_pasos)
            except (ValueError, TypeError):
                return Response({"error": "Los pasos deben ser un número entero."}, status=HTTP_400_BAD_REQUEST)

        if nuevos_pasos < 0:
            return Response({"error": "No se permiten pasos negativos."}, status=HTTP_400_BAD_REQUEST)

        hoy = date.today()

        with transaction.atomic():
            step_obj, _ = Pasos.objects.select_for_update().get_or_create(
                fk_usuarios=request.user,
                fecha=hoy,
                defaults={"pasos": 0}
            )

            step_obj.pasos += nuevos_pasos
            step_obj.save()

            multiplicador = calcular_multiplicador(request.user)
            monedas_adicionales = int((nuevos_pasos * multiplicador) // 200)

            request.user.pasos_totales += nuevos_pasos
            request.user.monedas_actuales += monedas_adicionales
            request.user.save()

        logger.info("%s agregó %s pasos (x%.1f). Monedas: +%s", request.user.email, nuevos_pasos, multiplicador, monedas_adicionales)

        return Response({
            "stepsToday": step_obj.pasos,
            "totalSteps": request.user.pasos_totales,
            "coins": request.user.monedas_actuales
        }, status=HTTP_200_OK)
"""