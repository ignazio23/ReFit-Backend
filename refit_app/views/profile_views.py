import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from django.utils import timezone
from django.shortcuts import get_object_or_404
import uuid
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from refit_app.serializers import (
    EditDailyObjetiveSerializer,
    EditPersonalDataSerializer,
    LoginResponseSerializer,
    UserSerializer
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
        serializer = UserSerializer(request.user, context={'request': request})
        logger.info("Detalles del usuario autenticado recuperados.")
        return Response(serializer.data, status=HTTP_200_OK)

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
    
    def patch(self, request):
        """
        Actualiza los datos personales del usuario autenticado.
        """
        user = request.user
        serializer = EditPersonalDataSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info("Datos del usuario autenticado actualizados.")
            return Response(LoginResponseSerializer(user).data, status=HTTP_200_OK)
        logger.error("Error al actualizar datos del usuario autenticado: %s", serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """
        Elimina lógicamente la cuenta del usuario (bloqueo + fecha de solicitud).
        """
        user = request.user
        if not user.is_active:
            return Response({"detail": "La cuenta ya fue desactivada permanentemente."}, status=HTTP_400_BAD_REQUEST)

        if user.blocked:
            return Response({"detail": "Tu cuenta ya está en proceso de eliminación."}, status=HTTP_200_OK)

        user.blocked = True
        user.lock_date = timezone.now()
        user.save()

        return Response({
            "message": "Cuenta marcada para eliminación lógica. Tienes 30 días para reactivarla con login."
        }, status=HTTP_200_OK)

# --------------------------------------------------------------------------
# Edición de imagen de perfil
# --------------------------------------------------------------------------
class UploadProfilePictureView(APIView):
    """
    Permite subir una imagen de perfil directamente desde la app (multipart/form-data).
    Guarda el archivo y lo asigna al perfil del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        archivo = request.FILES.get("image")

        if not archivo:
            return Response({"error": "No se ha enviado ninguna imagen."}, status=HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(archivo.name)[-1].lower()
        if ext not in ['.jpg', '.jpeg', '.png']:
            return Response({"error": "Formato no permitido. Solo JPG o PNG."}, status=HTTP_400_BAD_REQUEST)

        # Guardado en /media/public con nombre estandarizado
        img_uuid = str(uuid.uuid4())
        filename = f"{request.user.id}_profile{ext}"
        ruta_publica = os.path.join("public", filename)
        default_storage.save(ruta_publica, ContentFile(archivo.read()))

        imagen = Imagen.objects.create(uuid=img_uuid, extension=ext)
        request.user.image = imagen
        request.user.save()

        return Response({
            "message": "Imagen de perfil subida y asignada correctamente.",
            "imageUrl": f"http://3.17.152.152/media/public/{filename}"
        }, status=HTTP_200_OK)

# --------------------------------------------------------------------------
# Edición de datos y objetivo diario - Se unifica en UserDetailView
# --------------------------------------------------------------------------
"""
class EditPersonalDataView(APIView):
    ""
    Permite actualizar nombre, apellidos y email del usuario autenticado.
    ""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        ""
        Actualiza los datos personales del usuario autenticado.
        ""
        serializer = EditPersonalDataSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info("Datos personales actualizados para el usuario %s.", request.user.email)
            return Response({"detail": "Datos actualizados correctamente"}, status=HTTP_200_OK)
        logger.error("Error al actualizar datos personales para el usuario %s: %s", request.user.email, serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
"""
# --------------------------------------------------------------------------
# Edición del objetivo diario
# --------------------------------------------------------------------------
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
# Eliminación lógica de cuenta - Se unifica en UserDetailView
# --------------------------------------------------------------------------   
"""
class DeleteAccountView(APIView):
    ""
    Marca la cuenta del usuario autenticado para eliminación lógica en 30 días.
    ""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user

        if not user.is_active:
            return Response({"detail": "La cuenta ya fue desactivada permanentemente."}, status=HTTP_400_BAD_REQUEST)

        if user.blocked:
            return Response({"detail": "Tu cuenta ya está en proceso de eliminación."}, status=HTTP_200_OK)

        user.blocked = True
        user.lock_date = timezone.now()
        user.save()

        logger.info("El usuario %s ha solicitado la eliminación lógica de su cuenta.", user.email)

        return Response({
            "message": "Cuenta marcada para eliminación lógica. Tienes 30 días para reactivarla con login."
        }, status=HTTP_200_OK)
"""