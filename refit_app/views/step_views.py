from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from django.db import transaction
from datetime import datetime, date
from django.utils import timezone, now
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
        Permite actualizar pasos del usuario:
        - Si recibe una lista con objetos: realiza múltiples acciones según 'action'.
        - Si recibe un solo número de pasos: los suma al día actual.
        Actualiza el campo last_sync del usuario al final.
        """
        data = request.data

        if isinstance(data, list):
            with transaction.atomic():
                for item in data:
                    action = item.get("action")
                    steps = item.get("steps")
                    fecha_str = item.get("date")

                    if action not in ["add", "replace"]:
                        return Response({"error": f"Acción no válida: {action}"}, status=HTTP_400_BAD_REQUEST)
                    if not isinstance(steps, int) or steps < 0:
                        return Response({"error": "Los pasos deben ser un número entero positivo."}, status=HTTP_400_BAD_REQUEST)
                    if not fecha_str:
                        return Response({"error": "Falta el campo date."}, status=HTTP_400_BAD_REQUEST)

                    try:
                        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    except ValueError:
                        return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD."}, status=HTTP_400_BAD_REQUEST)

                    step_obj, _ = Pasos.objects.select_for_update().get_or_create(
                        fk_usuarios=request.user,
                        fecha=fecha,
                        defaults={"pasos": 0}
                    )

                    if action == "add":
                        step_obj.pasos += steps
                        request.user.pasos_totales += steps
                    elif action == "replace":
                        request.user.pasos_totales += (steps - step_obj.pasos)
                        step_obj.pasos = steps

                    step_obj.save()

                # Actualizar sincronización
                request.user.last_sync = now()
                request.user.save()

            return Response({"detail": "Pasos actualizados correctamente."}, status=HTTP_200_OK)

        # Fallback a la lógica anterior (formato antiguo)
        nuevos_pasos = data.get("pasos")

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
            request.user.last_sync = now()
            request.user.save()

        logger.info("%s agregó %s pasos (x%.1f). Monedas: +%s", request.user.email, nuevos_pasos, multiplicador, monedas_adicionales)

        return Response({
            "stepsToday": step_obj.pasos,
            "totalSteps": request.user.pasos_totales,
            "coins": request.user.monedas_actuales
        }, status=HTTP_200_OK)
