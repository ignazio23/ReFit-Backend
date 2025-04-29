import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from django.shortcuts import get_object_or_404

from refit_app.models import User, UserFollowing
from refit_app.serializers import (
    LeaderBoardSerializer,
    LoginResponseSerializer
)

logger = logging.getLogger(__name__)

# ============================================================================
# SOCIAL VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Vistas API relacionadas con amigos, seguidores y ranking.
# ============================================================================
# --------------------------------------------------------------------------
# Lista de amigos para seguir
# --------------------------------------------------------------------------
class FollowingFriendsView(APIView):
    """
    Lista usuarios disponibles para seguir y permite agregar o quitar seguidores.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve la lista de usuarios disponibles para seguir.
        Excluye al usuario autenticado y a los administradores.
        """
        usuarios = User.objects.exclude(pk=request.user.pk).exclude(is_staff=True)
        serializer = LeaderBoardSerializer(usuarios, many=True)
        logger.info("User %s requested following friends list.", request.user.email)
        return Response(serializer.data, status=HTTP_200_OK)

    def post(self, request):
        """
        Agrega o quita un usuario de la lista de amigos.
        """
        action = request.data.get("action")
        follow_id  = request.data.get("followId")
        if not follow_id :
            logger.error("User %s did not provide 'seguir' parameter.", request.user.email)
            return Response({"error": "Falta el ID del usuario a seguir."}, status=HTTP_400_BAD_REQUEST)
        seguido = get_object_or_404(User, pk=follow_id )

        if action == "agregar":
            # Verificar si ya se está siguiendo
            existing_relation = UserFollowing.objects.filter(user=request.user, following=seguido).first()
            if existing_relation:
                logger.info("User %s is already following user %s.", request.user.email, seguido.email)
                return Response({"message": "Ya estás siguiendo a este usuario."}, status=HTTP_200_OK)
            UserFollowing.objects.create(user=request.user, following=seguido)
            logger.info("User %s started following user %s.", request.user.email, seguido.email)
            return Response({"message": "Usuario agregado a tus seguidos."}, status=HTTP_200_OK)
        elif action == "borrar":
            deleted, _ = UserFollowing.objects.filter(user=request.user, following=seguido).delete()
            if deleted:
                logger.info("User %s unfollowed user %s.", request.user.email, seguido.email)
                return Response({"message": "Dejaste de seguir al usuario."}, status=HTTP_200_OK)
            else:
                logger.info("User %s was not following user %s.", request.user.email, seguido.email)
                return Response({"message": "No estabas siguiendo a este usuario."}, status=HTTP_200_OK)
        else:
            logger.error("Invalid action provided by user %s: %s", request.user.email, action)
            return Response({"error": "Acción inválida."}, status=HTTP_400_BAD_REQUEST)

# --------------------------------------------------------------------------
# Lista de amigos
# --------------------------------------------------------------------------
class FriendsView(APIView):
    """
    Devuelve la lista de amigos que el usuario está siguiendo actualmente.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve la lista de amigos que el usuario está siguiendo.
        """
        amigos = User.objects.filter(
            pk__in=UserFollowing.objects.filter(user=request.user).values_list('following', flat=True)
        )
        serializer = LeaderBoardSerializer(amigos, many=True)
        logger.info("User %s requested list of friends.", request.user.email)
        return Response(serializer.data, status=HTTP_200_OK)

# --------------------------------------------------------------------------
# Leaderboard
# --------------------------------------------------------------------------
class LeaderboardView(APIView):
    """
    Devuelve el top 5 de usuarios con más pasos en el sistema.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        top_users = User.objects.filter(is_staff=False).order_by('-pasos_totales')[:5]
        serializer = LeaderBoardSerializer(top_users, many=True, context={'request': request})

        # Agregar campo de ranking manualmente
        data = serializer.data
        for idx, user in enumerate(data, start=1):
            user["ranking"] = idx

        return Response(data, status=HTTP_200_OK)
    
# --------------------------------------------------------------------------
# Ranking del usuario autenticado
# --------------------------------------------------------------------------
class UsuarioRankingView(APIView):
    """
    Devuelve la posición del usuario autenticado en el ranking de pasos.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve la posición del usuario autenticado en el ranking de pasos.
        """
        usuarios = User.objects.filter(is_staff=False).order_by('-pasos_totales').values_list('id', flat=True)
        try:
            posicion = list(usuarios).index(request.user.id) + 1
        except ValueError:
            posicion = None

        serializer = LoginResponseSerializer(request.user)
        data = serializer.data
        data['leaderBoardPosition'] = posicion

        return Response(data, status=HTTP_200_OK) 