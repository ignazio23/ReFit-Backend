from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

from refit_app.views.auth_views import (
    RegisterView, LoginView, LogOutView, ChangePasswordView,
    PasswordRecoveryView, ResetPasswordView
)
from refit_app.views.profile_views import (
    UserDetailView, EditProfilePictureView, EditDailyGoalView, EditPersonalDataView,
    UserLastLoginView
)
from refit_app.views.product_views import (
    ProductView, ExchangeProductView, CategoriaCreateView, EditProductImageView,
    ProductoCreateView, CategoriaListView, CategoriaEditView, ProductoEditView
)
from refit_app.views.task_views import (
    CheckDailyTaskView, ExchangeDailyTaskView, ObjetivoDiarioCreateView, 
    ObjetivoDiarioListView, ObjetivosActivosUsuarioView, ObjetivoDiarioEditView
)
from refit_app.views.step_views import StepUpdateView
from refit_app.views.social_views import FollowingFriendsView, LeaderboardView, UsuarioRankingView
from refit_app.views.contact_views import ContactUsView
from refit_app.views.advanced_views import (
    ReferredUsersView, RecompensasParametrosView, HistoricalStepsView, 
    HistoricalCanjesView, UploadImageView, ServeImageView
)
from refit_app.views.status_views import RefreshTimestampView  

# ==========================================================================
# URLS – ReFit App (reestructurado según SQL)
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/06
# Descripción: Este archivo define las rutas (endpoints) de la API de ReFit.
#              Se han consolidado y verificado todos los endpoints para evitar duplicaciones y asegurar
#              que cada vista tenga su correspondiente ruta.
# ==========================================================================

urlpatterns = [
    # Autenticación y credenciales
    path("auth/", include([
        path("register/", RegisterView.as_view(), name="register"),
        path("login/", LoginView.as_view(), name="login"),
        path("logout/", LogOutView.as_view(), name="logout"),
        path("change-password/", ChangePasswordView.as_view(), name="change-password"),
        path("recover-password/", PasswordRecoveryView.as_view(), name="recover-password"),
        path("auth/reset-password/", ResetPasswordView.as_view(), name="reset-password"),
        # Endpoint de TOKENS JWT
        path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
        path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
        # Endpoint para actualizar y retornar la fecha/hora de última actualización
        path("status/refresh/", RefreshTimestampView.as_view(), name="refresh-timestamp"),
    ])),

    # Perfil de usuario
    path("users/", include([
        path("profile/", UserDetailView.as_view(), name="user-profile"),
        path("edit-profile/", EditPersonalDataView.as_view(), name="edit-user"),
        path("profile-picture/", EditProfilePictureView.as_view(), name="perfil-imagen"),
        path("daily-goal/", EditDailyGoalView.as_view(), name="edit-daily-goal"),
        path("last-login/", UserLastLoginView.as_view(), name="user-last-login"),
        path("referred/", ReferredUsersView.as_view(), name="user-referred"),
    ])),

    # Conteo de pasos diarios
    path("steps/", StepUpdateView.as_view(), name="pasos-diarios"),

    # Objetivos y tareas diarias
    path("objectives/", include([
        path("crear/", ObjetivoDiarioCreateView.as_view(), name="crear_objetivo_diario"),
        path('<int:objetivo_id>/editar/', ObjetivoDiarioEditView.as_view()),
        path("listar/", ObjetivoDiarioListView.as_view(), name="listar-objetivos"),
        path("activos/", ObjetivosActivosUsuarioView.as_view(), name="objetivos-usuario"),
        path("check/", CheckDailyTaskView.as_view(), name="check-objetivo"),
        path("canjear/", ExchangeDailyTaskView.as_view(), name="canjear-objetivo"),
    ])),

    # Productos y sistema de canje
    path("products/", include([
        path("view/", ProductView.as_view(), name="product-list"),
        path("canjear/", ExchangeProductView.as_view(), name="exchange-product"),
        path("nueva_categoria/", CategoriaCreateView.as_view(), name="nueva_categoria"),
        path("categorias/", CategoriaListView.as_view(), name="listar_categorias"),
        path("categorias/editar/<int:id_categoria>/", CategoriaEditView.as_view(), name="editar_categoria"),
        path("nuevo/", ProductoCreateView.as_view(), name="nuevo_producto"),
        path("editar/<int:id_producto>/", ProductoEditView.as_view(), name="editar_producto"),
        path("producto/<int:producto_id>/imagen/", EditProductImageView.as_view(), name="producto-imagen"),
    ])),

    # Interacciones sociales y ranking
    path("social/", include([
        path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),
        path("friends/", FollowingFriendsView.as_view(), name="following-friends"),
        path("ranking/", UsuarioRankingView.as_view(), name="usuario-ranking"),
    ])),

    # Parámetros y vistas avanzadas
    path("config/", include([
        path("rewards/", RecompensasParametrosView.as_view(), name="config-rewards"),
    ])),

    # Carga de imágenes (usuarios y productos)
    path("upload/imagen/", UploadImageView.as_view(), name="upload-imagen"),
    path("ver-imagen/<str:filename>/", ServeImageView.as_view(), name="ver-imagen"),

    # Historial de pasos y canjes
    path("history/", include([
        path("steps/", HistoricalStepsView.as_view(), name="history-steps"),
        path("redemptions/", HistoricalCanjesView.as_view(), name="history-redemptions"),
    ])),

    # Contacto con soporte o feedback
    path("contact/", ContactUsView.as_view(), name="contact-us"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)