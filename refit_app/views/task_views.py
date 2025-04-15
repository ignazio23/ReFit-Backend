import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from django.utils import timezone
from django.db.models import Q
from datetime import date, timedelta
from django.shortcuts import get_object_or_404

from refit_app.models import ObjetivoDiario, UsuarioObjetivoDiario, User
from refit_app.serializers import (
    ObjetivoDiarioSerializer,
    UsuarioObjetivoDiarioSerializer,
    EditDailyObjetiveSerializer,
    CheckDailyTaskSerializer,
    ExchangeDailyTaskSerializer
)

from refit_app.services.objetivos_service import puede_completar_objetivo

logger = logging.getLogger(__name__)

# ============================================================================
# TASK VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Vistas placeholder para verificación y canje de tareas diarias.
# ============================================================================

def calcular_multiplicador(user):
    """
    Calcula el multiplicador basado en la racha del usuario.
    Si han pasado 24 horas desde la última actualización de la racha
    sin que se haya incrementado, se reinicia la racha a 0.
    """
    if user.racha_updated_at:
        if timezone.now() - user.racha_updated_at >= timedelta(hours=24):
            user.racha = 0
            user.racha_updated_at = None
            user.save()
            return 1.0  # Valor base
    return min(2.0, 1.0 + 0.1 * user.racha)

# --------------------------------------------------------------------------
# Crear un objetivo diario general (Admin)
# --------------------------------------------------------------------------
class ObjetivoDiarioCreateView(APIView):
    """
    Permite a un administrador crear un objetivo diario general.
    Este objetivo será visible para todos los usuarios como parte de las tareas diarias.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Crea un nuevo objetivo diario general con nombre, descripción y premio.
        Valida que el premio sea mayor a cero.
        """
        serializer = ObjetivoDiarioSerializer(data=request.data)
        if serializer.is_valid():
            objetivo = serializer.save()
            logger.info("Objetivo diario creado por %s: %s", request.user.email, objetivo.nombre)
            return Response({
                "message": "Objetivo diario creado con éxito.",
                "objetivo": serializer.data
            }, status=HTTP_201_CREATED)

        logger.error("Error al crear objetivo diario: %s", serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

# --------------------------------------------------------------------------
# Editar un objetivo diario general (Admin)
# --------------------------------------------------------------------------
class ObjetivoDiarioEditView(APIView):
    """
    Permite a un administrador editar parcialmente un objetivo diario existente.
    Requiere el ID del objetivo en la URL.
    """
    permission_classes = [IsAdminUser]

    def patch(self, request, objetivo_id):
        """
        Edita parcialmente un objetivo diario por su ID.
        Permite modificar nombre, descripción o premio.
        """
        objetivo = get_object_or_404(ObjetivoDiario, pk_objetivos_diarios=objetivo_id)

        serializer = ObjetivoDiarioSerializer(objetivo, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info("Objetivo diario %s editado por %s", objetivo_id, request.user.email)
            return Response({
                "message": "Objetivo actualizado correctamente.",
                "objetivo": serializer.data
            }, status=HTTP_200_OK)

        logger.error("Error al editar objetivo %s: %s", objetivo_id, serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
# --------------------------------------------------------------------------
# Listado de objetivos generales (visibles para admins o usuarios si se desea)
# --------------------------------------------------------------------------
class ObjetivoDiarioListView(APIView):
    """
    Permite a un administrador listar todos los objetivos diarios generales.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Lista todos los objetivos diarios generales.
        """
        objetivos = ObjetivoDiario.objects.all().order_by('-fecha_creacion')
        serializer = ObjetivoDiarioSerializer(objetivos, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

# --------------------------------------------------------------------------
# Ver objetivos diarios activos para el usuario autenticado
# --------------------------------------------------------------------------
class ObjetivosActivosUsuarioView(APIView):
    """
    Permite a un usuario autenticado ver sus objetivos diarios activos.
    Si no tiene objetivos activos para el día actual, se crean automáticamente.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Lista los objetivos diarios activos para el usuario autenticado.
        Si no tiene objetivos activos para el día actual, se crean automáticamente.
        """
        hoy = date.today()

        # Activar automáticamente si no tiene tareas activas hoy
        existentes = UsuarioObjetivoDiario.objects.filter(fk_usuarios=request.user, fecha_creacion=hoy)
        if not existentes.exists():
            generales = ObjetivoDiario.objects.all()
            nuevos = [
                UsuarioObjetivoDiario(
                    fk_usuarios=request.user,
                    fk_objetivos_diarios=obj
                ) for obj in generales
            ]
            UsuarioObjetivoDiario.objects.bulk_create(nuevos)
            logger.info("Objetivos diarios activados para %s.", request.user.email)

        tareas = UsuarioObjetivoDiario.objects.filter(fk_usuarios=request.user, fecha_creacion=hoy)
        serializer = UsuarioObjetivoDiarioSerializer(tareas, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
# --------------------------------------------------------------------------
# Marcar tarea como completada y evaluar racha
# --------------------------------------------------------------------------
class CheckDailyTaskView(APIView):
    """
    Permite al usuario marcar una tarea diaria como completada.
    Si completa todas las tareas del día, se incrementa su racha.
    Si no completa todas las tareas en 24 horas, se reinicia la racha.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Marca una tarea diaria como completada.
        Si el usuario completa todas las tareas del día, se incrementa su racha.
        """
        serializer = CheckDailyTaskSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            tarea = serializer.tarea

            # Verificar que se hayan cumplido los pasos requeridos
            if not puede_completar_objetivo(tarea):
                return Response({"error": "No se alcanzó el objetivo de pasos."}, status=HTTP_400_BAD_REQUEST)

            tarea.fecha_completado = timezone.now()
            tarea.save()
            logger.info("Tarea %s marcada como completada para %s", tarea.pk, request.user.email)

            # Verificar si el usuario completó todas las tareas de hoy
            hoy = date.today()
            completadas = UsuarioObjetivoDiario.objects.filter(
                fk_usuarios=request.user,
                fecha_creacion=hoy,
                fecha_completado__isnull=False
            ).count()
            total = UsuarioObjetivoDiario.objects.filter(
                fk_usuarios=request.user,
                fecha_creacion=hoy
            ).count()

            if completadas == total:
                request.user.racha += 1
                request.user.racha_updated_at = timezone.now()
                request.user.save()
                logger.info("%s completó todos los objetivos. Racha actual: %s", request.user.email, request.user.racha)

            return Response({"message": "Tarea completada correctamente."}, status=HTTP_200_OK)
        logger.error("Error al verificar tarea: %s", serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

# --------------------------------------------------------------------------
# Canjear recompensa y aplicar multiplicador según racha
# --------------------------------------------------------------------------
class ExchangeDailyTaskView(APIView):
    """
    Permite al usuario canjear una recompensa diaria.
    Aplica un multiplicador basado en la racha del usuario,
    reiniciando la racha si han pasado 24 horas sin un incremento.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Canjea una recompensa diaria.
        Aplica un multiplicador basado en la racha del usuario.
        """
        serializer = ExchangeDailyTaskSerializer(data=request.data, context={'request': request})

        # Verificar si la tarea existe
        if tarea.fecha_canjeado:
            return Response({"error": "La tarea ya fue canjeada."}, status=HTTP_400_BAD_REQUEST)

        # Verificar si la tarea fue completada
        if not tarea.fecha_completado:
            return Response({"error": "La tarea aún no ha sido completada."}, status=HTTP_400_BAD_REQUEST)

        if serializer.is_valid():
            tarea = serializer.tarea
            tarea.fecha_canjeado = timezone.now()
            tarea.save()

            # Calcular el multiplicador con la función helper
            multiplicador = calcular_multiplicador(request.user.racha)
            premio_base = tarea.fk_objetivos_diarios.premio
            premio_final = int(premio_base * multiplicador)

            request.user.monedas_actuales += premio_final
            request.user.save()

            logger.info("Tarea %s canjeada por %s. Multiplicador: %.1f", tarea.pk, request.user.email, multiplicador)

            return Response({
                "message": "Recompensa canjeada exitosamente.",
                "premio": premio_base,
                "multiplicador": multiplicador,
                "total_recibido": premio_final
            }, status=HTTP_200_OK)
        logger.error("Error al canjear tarea: %s", serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
