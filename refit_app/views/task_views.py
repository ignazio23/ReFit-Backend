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
    - Solo se aplica si el usuario ha completado TODOS los objetivos del día actual.
    - Si han pasado más de 24h desde la última racha (racha_updated_at), se reinicia.
    """
    ahora = timezone.now()

    if user.racha_updated_at:
        tiempo_desde_ultima_racha = ahora - user.racha_updated_at
        if tiempo_desde_ultima_racha > timedelta(hours=24):
            # 🔁 Reinicia si no se completaron todos los objetivos en ese intervalo
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
        Devuelve la lista de objetivos diarios activos para todos los usuarios.
        """
        objetivos = ObjetivoDiario.objects.filter(is_active=True).order_by('pk_objetivos_diarios')
        serializer = ObjetivoDiarioSerializer(objetivos, many=True)
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

        if not serializer.is_valid():
            logger.error("Error al verificar tarea diaria: %s", serializer.errors)
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        tarea = serializer.tarea
        objetivo = tarea.fk_objetivos_diarios

        # Solo se permiten tareas de tipo cuantitativo desde esta lógica
        if objetivo.tipo != "cuantitativo":
            return Response({"error": "Este tipo de objetivo no puede completarse manualmente."}, status=HTTP_400_BAD_REQUEST)

        if tarea.fecha_completado:
            return Response({"message": "La tarea ya fue marcada como completada."}, status=HTTP_200_OK)

        if not puede_completar_objetivo(tarea):
            return Response({"error": "No se alcanzó el requisito del objetivo."}, status=HTTP_400_BAD_REQUEST)

        # Marcar como completada
        tarea.fecha_completado = timezone.now()
        tarea.save()
        logger.info("Tarea %s marcada como completada para %s", tarea.pk, request.user.email)

        # Verificar si el usuario completó todas las tareas del día
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

        if serializer.is_valid():
            tarea = serializer.tarea

            # Validación ya fue hecha en el serializer (completado y no canjeado)
            tarea.fecha_canjeado = timezone.now()
            tarea.save()

            premio_base = tarea.fk_objetivos_diarios.premio
            request.user.monedas_actuales += premio_base
            request.user.save()

            logger.info("Tarea %s canjeada por %s. Premio: %s", tarea.pk, request.user.email, premio_base)

            return Response({
                "message": "Recompensa canjeada exitosamente.",
                "prize": premio_base
            }, status=HTTP_200_OK)

        logger.error("Error al canjear tarea: %s", serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
