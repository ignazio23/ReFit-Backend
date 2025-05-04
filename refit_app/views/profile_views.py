import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from django.utils import timezone
from django.shortcuts import get_object_or_404
import uuid
import os
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

from refit_app.serializers import (
    EditDailyObjetiveSerializer,
    EditPersonalDataSerializer,
    LoginResponseSerializer,
    UserSerializer,
    PublicUserProfileSerializer
)
from refit_app.models import User, Imagen

logger = logging.getLogger(__name__)

# ============================================================================
# PROFILE VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/28
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
            data = UserSerializer(user).data
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
            return Response(UserSerializer(user).data, status=HTTP_200_OK)
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
    Reemplaza el archivo anterior en /media/public/, elimina su registro en la base,
    guarda la nueva imagen con el mismo nombre fijo y la asigna al usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        archivo = request.FILES.get("image")
        if not archivo:
            return Response({"error": "No se ha enviado ninguna imagen."}, status=HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(archivo.name)[-1].lower()
        if ext not in [".jpg", ".jpeg", ".png"]:
            return Response({"error": "Formato no permitido. Solo JPG o PNG."}, status=HTTP_400_BAD_REQUEST)

        user_id = request.user.id
        nombre_logico = f"{user_id}_profile"
        filename = f"{nombre_logico}{ext}"
        ruta_relativa = os.path.join("public", filename)
        ruta_absoluta = os.path.join(settings.MEDIA_ROOT, ruta_relativa)

        # Borrar archivo físico anterior (si existe)
        if os.path.exists(ruta_absoluta):
            os.remove(ruta_absoluta)

        # Borrar imagen anterior en base de datos
        if request.user.image_id:
            Imagen.objects.filter(pk=request.user.image_id).delete()

        # Guardar archivo nuevo en la misma ruta
        default_storage.save(ruta_relativa, ContentFile(archivo.read()))

        # Crear nueva entrada en la tabla IMAGENES
        nueva_imagen = Imagen.objects.create(
            uuid=uuid.uuid4(),
            extension=ext,
            nombre_logico=nombre_logico
        )

        # Asignar al usuario
        request.user.image = nueva_imagen
        request.user.save()

        # Forzar caché-busting agregando UUID en la URL (sin cambiar nombre lógico en disco)
        return Response({
            "message": "Imagen de perfil actualizada correctamente.",
            "imageUrl": f"http://3.17.152.152/media/public/{filename}?v={nueva_imagen.uuid}"
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
# Visualización de otros Usuarios
# --------------------------------------------------------------------------   
class PublicUserProfileView(APIView):
    """
    Permite obtener el perfil público de un usuario por ID,
    o buscar usuarios por nombre y apellido si no se pasa ID.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        name = request.query_params.get('name')
        surname = request.query_params.get('surname')

        if user_id:
            user = get_object_or_404(User, pk=user_id, is_active=True)
            serializer = PublicUserProfileSerializer(user, context={'request': request})
            return Response(serializer.data, status=HTTP_200_OK)

        elif name or surname:
            filters = Q()
            if name:
                filters &= Q(nombre__icontains=name)
            if surname:
                filters &= Q(apellidos__icontains=surname)

            users = User.objects.filter(filters, is_active=True)
            serializer = PublicUserProfileSerializer(users, many=True, context={'request': request})
            return Response(serializer.data, status=HTTP_200_OK)

        return Response({"error": "Debe proporcionar un userId o parámetros de búsqueda."}, status=400)
