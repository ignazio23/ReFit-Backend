from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from django.db import transaction
from datetime import datetime, date

from refit_app.models import Pasos

# ============================================================================
# STEP VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Vistas API relacionadas con el conteo de pasos diarios.
# ============================================================================
# --------------------------------------------------------------------------
# Registro y consulta de pasos diarios
# --------------------------------------------------------------------------
class StepCountView(APIView):
    """
    Permite registrar pasos del día y consultar pasos actuales.
    Sobrescribe el valor de pasos si ya existe.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Registra los pasos del día para el usuario autenticado.
        Si el registro ya existe, lo sobrescribe.
        """
        pasos = request.data.get("pasos")
        timestamp_str = request.data.get("timestamp") or str(date.today())

        try:
            fecha_obj = datetime.strptime(timestamp_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Formato de fecha inválido. Se espera YYYY-MM-DD."}, status=HTTP_400_BAD_REQUEST)

        if not isinstance(pasos, int):
            try:
                pasos = int(pasos)
            except (ValueError, TypeError):
                return Response({"error": "Los pasos deben ser un número entero."}, status=HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            step_obj, created = Pasos.objects.select_for_update().get_or_create(
                fk_usuarios=request.user,
                fecha=fecha_obj,
                defaults={"pasos": pasos}
            )

            diferencia = pasos - step_obj.pasos if not created else pasos

            if diferencia < 0:
                return Response({"error": "No se permiten pasos regresivos."}, status=HTTP_400_BAD_REQUEST)

            if not created:
                step_obj.pasos = pasos
                step_obj.save()

            request.user.pasos_totales += diferencia
            request.user.monedas_actuales += diferencia // 200  # 1 moneda cada 200 pasos
            request.user.save()

        return Response({
            "pasos_hoy": step_obj.pasos,
            "pasos_totales": request.user.pasos_totales,
            "monedas": request.user.monedas_actuales
        }, status=HTTP_200_OK)

    def get(self, request):
        """
        Consulta los pasos del día actual para el usuario autenticado.
        Devuelve pasos actuales, totales y monedas.
        """
        step_obj = Pasos.objects.filter(fk_usuarios=request.user, fecha=date.today()).first()
        pasos = step_obj.pasos if step_obj else 0
        return Response({
            "pasos_hoy": pasos,
            "pasos_totales": request.user.pasos_totales,
            "monedas": request.user.monedas_actuales
        }, status=HTTP_200_OK)


class AddStepsView(APIView):
    """
    Suma pasos al registro del día del usuario autenticado.
    Crea el registro si no existe. Aplica lógica de monedas.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """
        Suma pasos al registro del día del usuario autenticado.
        Si el registro no existe, lo crea. Aplica lógica de monedas.
        """
        nuevos_pasos = request.data.get("pasos")

        if not isinstance(nuevos_pasos, int):
            try:
                nuevos_pasos = int(nuevos_pasos)
            except (ValueError, TypeError):
                return Response({"error": "Los pasos deben ser un número entero."}, status=HTTP_400_BAD_REQUEST)

        if nuevos_pasos < 0:
            return Response({"error": "No se permiten pasos negativos."}, status=HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            step_obj, _ = Pasos.objects.select_for_update().get_or_create(
                fk_usuarios=request.user,
                fecha=date.today(),
                defaults={"pasos": 0}
            )

            step_obj.pasos += nuevos_pasos
            step_obj.save()

            request.user.pasos_totales += nuevos_pasos
            request.user.monedas_actuales += nuevos_pasos // 200
            request.user.save()

        return Response({
            "pasos_hoy": step_obj.pasos,
            "pasos_totales": request.user.pasos_totales,
            "monedas": request.user.monedas_actuales
        }, status=HTTP_200_OK)