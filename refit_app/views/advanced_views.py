import uuid
import os
import logging
from django.conf import settings
from django.http import FileResponse, Http404
import mimetypes
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.files.base import ContentFile
from rest_framework.response import Response
from django.core.files.storage import default_storage
from datetime import datetime
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from refit_app.models import User, Parametro, Pasos, Canje, Imagen, FAQ
from refit_app.serializers import (
    ReferredUserSerializer,
    RecompensaParametroSerializer,
    HistoricalStepsSerializer,
    HistoricalCanjeSerializer,
    ImagenSerializer,
    FAQSerializer
)

logger = logging.getLogger(__name__)

# ============================================================================
# ADVANCED VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Vistas de funcionalidad avanzada para la API de ReFit.
# ============================================================================
# ---------------------------------------------------------------------------
# USUARIOS REFERIDOS
# ---------------------------------------------------------------------------
class ReferredUsersView(APIView):
    """
    Devuelve los usuarios referidos por el usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve los usuarios referidos por el usuario autenticado.
        """
        referidos = User.objects.filter(fk_usuario_referente=request.user)
        data = ReferredUserSerializer(referidos, many=True).data
        logger.info("User %s requested referred users.", request.user.email)
        return Response(data, status=HTTP_200_OK)
    
    def post(self, request):
        referral_code = request.data.get("code")

        if not referral_code:
            return Response({"error": "Debe enviar el código del referente."}, status=HTTP_400_BAD_REQUEST)

        if request.user.fk_usuario_referente is not None:
            return Response({"error": "Ya tiene un usuario referente asignado."}, status=HTTP_400_BAD_REQUEST)

        try:
            referente = User.objects.get(codigo_referido=referral_code, is_active=True)
        except User.DoesNotExist:
            return Response({"error": "El código de referido no es válido."}, status=HTTP_400_BAD_REQUEST)

        request.user.fk_usuario_referente = referente
        request.user.save()

        logger.info("Usuario %s asignó como referente a %s", request.user.email, referente.email)
        return Response({"message": "Usuario referente asignado correctamente."}, status=HTTP_200_OK)

# ----------------------------------------------------------------------------
# PARÁMETROS DE RECOMPENSA
# ----------------------------------------------------------------------------
class RecompensasParametrosView(APIView):
    """
    Devuelve los parámetros de recompensa.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve los parámetros de recompensa.
        """
        parametros = Parametro.objects.filter(codigo__startswith="RECOMPENSA_")
        data = RecompensaParametroSerializer(parametros, many=True).data
        logger.info("User %s requested reward parameters.", request.user.email)
        return Response(data, status=HTTP_200_OK)

# ----------------------------------------------------------------------------
# HISTORIAL DE PASOS Y CANJES
# ----------------------------------------------------------------------------
class HistoricalStepsView(APIView):
    """
    Devuelve el historial de pasos del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve el historial de pasos del usuario autenticado.
        """
        user = request.user
        start_date_str = request.query_params.get('startDate')
        end_date_str = request.query_params.get('endDate')

        # Sin fechas -> solo los pasos de hoy
        if not start_date_str or not end_date_str:
            today = datetime.now().date()
            steps = Pasos.objects.filter(fk_usuarios=user, fecha=today).order_by('-fecha')
        else:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Formato inválido. Use YYYY-MM-DD para startDate y endDate."},
                    status=400
                )

            steps = Pasos.objects.filter(
                fk_usuarios=user,
                fecha__range=(start_date, end_date)
            ).order_by('-fecha')

        data = HistoricalStepsSerializer(steps, many=True).data

        logger.info("User %s requested historical steps.", user.email)
        return Response(data, status=HTTP_200_OK)

# ----------------------------------------------------------------------------
# HISTORIAL DE CANJES
# ----------------------------------------------------------------------------
class HistoricalCanjesView(APIView):
    """
    Devuelve el historial de canjes del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve el historial de canjes del usuario autenticado.
        """
        canjes = Canje.objects.filter(fk_usuarios=request.user).order_by('-fecha')
        data = HistoricalCanjeSerializer(canjes, many=True).data
        logger.info("User %s requested historical redemptions.", request.user.email)
        return Response(data, status=HTTP_200_OK)
    
# --------------------------------------------------------------------------
# UPLOAD DE IMÁGENES CON UUID
# --------------------------------------------------------------------------
class UploadImageView(APIView):
    """
    Recibe un archivo de imagen (.jpg, .png), lo guarda con UUID y lo registra.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        archivo = request.FILES.get('imagen')

        if not archivo:
            return Response({"error": "No se ha enviado ningún archivo."}, status=HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(archivo.name)[-1].lower()
        if ext not in ['.jpg', '.jpeg', '.png']:
            return Response({"error": "Formato no permitido. Solo JPG o PNG."}, status=HTTP_400_BAD_REQUEST)

        img_uuid = str(uuid.uuid4())
        filename = f"{request.user.id}_profilepicture{ext}"
        ruta_publica = os.path.join("public", filename)
        default_storage.save(ruta_publica, ContentFile(archivo.read()))

        imagen = Imagen.objects.create(uuid=img_uuid, extension=ext)

        return Response({
            "uuid": imagen.uuid,
            "fileName": filename,
            "url": f"http://3.17.152.152/media/public/{filename}"
        }, status=HTTP_201_CREATED)

# ----------------------------------------------------------------------------
# SERVICIO DE IMÁGENES
# ----------------------------------------------------------------------------
class ServeImageView(APIView):
    """
    Sirve una imagen almacenada en /media/ si existe, usando su UUID con extensión.
    Uso: /ver-imagen/<uuid>.jpg
    """
    def get(self, request, filename):
        """
        Busca una imagen por UUID y devuelve su URL pública completa.
        """
        try:
            imagen = Imagen.objects.get(uuid=filename)
        except Imagen.DoesNotExist:
            return Response({"error": "Imagen no encontrada."}, status=HTTP_404_NOT_FOUND)

        public_url = f"http://3.17.152.152/media/public/{imagen.uuid}.{imagen.extension.strip('.')}"

        return Response({
            "uuid": imagen.uuid,
            "url": public_url
        }, status=HTTP_200_OK)
    
# ------------------------------------------------------------------------------
# FAQ
# ------------------------------------------------------------------------------
class FAQListView(APIView):
    """
    Devuelve la lista de FAQs.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        faqs = FAQ.objects.all().order_by('id')
        serializer = FAQSerializer(faqs, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
