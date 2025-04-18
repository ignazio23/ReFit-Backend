import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from django.utils import timezone
from django.shortcuts import get_object_or_404

from refit_app.serializers import (
    EditProfilePictureSerializer,
    EditDailyObjetiveSerializer,
    EditPersonalDataSerializer,
    LoginResponseSerializer
)
from refit_app.models import User, Imagen

logger = logging.getLogger(__name__)

# ============================================================================
# PROFILE VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Vistas API relacionadas al perfil del usuario y su edición.
# ============================================================================
# --------------------------------------------------------------------------
# Ver y editar perfil de usuario
# --------------------------------------------------------------------------
class UserDetailView(APIView):
    """
    Devuelve los datos del usuario autenticado.
    Ya no requiere ID por parámetro, usa el token de autenticación.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve los datos del usuario autenticado.
        """
        user = request.user
        data = LoginResponseSerializer(user).data
        logger.info("Detalles del usuario autenticado recuperados.")
        return Response(data, status=HTTP_200_OK)

    def put(self, request):
        """
        Actualiza los datos del usuario autenticado.
        """
        user = request.user
        serializer = EditPersonalDataSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info("Datos del usuario autenticado actualizados.")
            data = LoginResponseSerializer(user).data
            return Response(data, status=HTTP_200_OK)
        logger.error("Error al actualizar datos del usuario autenticado: %s", serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

# --------------------------------------------------------------------------
# Edición parcial del perfil autenticado
# --------------------------------------------------------------------------
class EditProfilePictureView(APIView):
    """
    Asocia una imagen subida previamente al perfil del usuario.
    Requiere enviar: { "imagen_id": 5 }
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """
        Actualiza la imagen de perfil del usuario autenticado.
        """
        imagen_id = request.data.get("imagen_id")
        uuid = request.data.get("uuid")
        uuid_completo = request.data.get("uuid_completo")

        imagen = None

        if imagen_id:
            imagen = Imagen.objects.filter(pk_imagenes=imagen_id).first()
        elif uuid:
            imagen = Imagen.objects.filter(uuid=uuid).first()
        elif uuid_completo:
            if "." in uuid_completo:
                uuid_part, ext = uuid_completo.rsplit(".", 1)
                imagen = Imagen.objects.filter(uuid=uuid_part, extension=f".{ext.lower()}").first()

        if not imagen:
            return Response({"error": "Imagen no encontrada. Verifique el identificador proporcionado."},
                            status=HTTP_400_BAD_REQUEST)

        request.user.image = imagen
        request.user.save()

        return Response({
            "detail": "Imagen de perfil actualizada correctamente.",
            "image_url": f"/media/{imagen.uuid}{imagen.extension}"
        }, status=HTTP_200_OK)
    
class EditPersonalDataView(APIView):
    """
    Permite actualizar nombre, apellidos y email del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """
        Actualiza los datos personales del usuario autenticado.
        """
        serializer = EditPersonalDataSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info("Datos personales actualizados para el usuario %s.", request.user.email)
            return Response({"detail": "Datos actualizados correctamente"}, status=HTTP_200_OK)
        logger.error("Error al actualizar datos personales para el usuario %s: %s", request.user.email, serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

class EditDailyGoalView(APIView):
    """
    Permite modificar el objetivo diario de pasos del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """
        Actualiza el objetivo diario de pasos del usuario autenticado.
        """
        serializer = EditDailyObjetiveSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info("Objetivo diario actualizado para el usuario %s.", request.user.email)
            return Response({"detail": "Objetivo diario actualizado"}, status=HTTP_200_OK)
        logger.error("Error al actualizar objetivo diario para el usuario %s: %s", request.user.email, serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
# --------------------------------------------------------------------------
# Visualización de última conexión
# --------------------------------------------------------------------------
class UserLastLoginView(APIView):
    """
    Devuelve la fecha y hora de la última conexión del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve la fecha y hora de la última conexión del usuario autenticado.
        """
        user = request.user
        ultimo_login = user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else None
        return Response({"ultimo_login": ultimo_login}, status=HTTP_200_OK)

# --------------------------------------------------------------------------
# Eliminación lógica de cuenta
# --------------------------------------------------------------------------   
class DeleteAccountView(APIView):
    """
    Marca la cuenta del usuario autenticado para eliminación lógica en 30 días.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.bloqueated:
            return Response({"detail": "Ya has solicitado eliminar tu cuenta."}, status=HTTP_400_BAD_REQUEST)

        user.bloqueated = True
        user.lock_date = timezone.now()
        user.save()

        logger.info("Usuario %s marcó su cuenta para eliminación lógica.", user.email)

        return Response({"message": "La cuenta será eliminada en 30 días si no inicias sesión."}, status=HTTP_200_OK)
