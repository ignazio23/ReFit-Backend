from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

from refit_app.views.auth_views import (
    RegisterView, LoginView, LogOutView, ChangePasswordView,
    PasswordRecoveryView
)
from refit_app.views.profile_views import (
    UserDetailView, EditDailyGoalView, 
    UploadProfilePictureView, UserLastLoginView
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
    # Autenticación
    path("auth/", include([
        path("register/", RegisterView.as_view(), name="register"),                             # POST
        path("login/", LoginView.as_view(), name="login"),                                      # POST
        path("logout/", LogOutView.as_view(), name="logout"),                                   # POST
        path("update-password/", ChangePasswordView.as_view(), name="change-password"),         # PATCH
        path("reset-password/", PasswordRecoveryView.as_view(), name="reset-password"),         # POST
        # Endpoint de TOKENS JWT
        path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),                # POST
        path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),               # POST
        # Endpoint para actualizar y retornar la fecha/hora de última actualización
        path("status/refresh/", RefreshTimestampView.as_view(), name="refresh-timestamp"),      # POST
    ])),

    # Usuario y Perfil
    path("users/me/", include([
        path("", UserDetailView.as_view(), name="user-profile"),                                # GET / PUT/PATCH / DELETE
        path("profile-picture/", UploadProfilePictureView.as_view(), name="profile-picture"),   # PATCH
        path("daily-goal/", EditDailyGoalView.as_view(), name="edit-daily-goal"),               # PATCH
        path("last-login/", UserLastLoginView.as_view(), name="user-last-login"),               # GET
        path("referrals/", ReferredUsersView.as_view(), name="user-referred"),                  # GET 
    ])),

    # Conteo de Pasos
    path("steps/", include([
        path("", StepUpdateView.as_view(), name="daily_steps"),                                 # GET / PATCH
        path("me/", HistoricalStepsView.as_view(), name="history-steps"),                       # GET
    ])),
    
    # Objetivos Diarios
    path("objectives/", include([
        path("", ObjetivoDiarioListView.as_view(), name="list-objetives"),                      # GET
        path("create/", ObjetivoDiarioCreateView.as_view(), name="create_daily_objetive"),      # POST
        path("<int:objetivo_id>/edit/", ObjetivoDiarioEditView.as_view(), name="edit-objetive"),# PUT / PATCH
        path("actives/", ObjetivosActivosUsuarioView.as_view(), name="objetives-user"),         # GET
        path("check/", CheckDailyTaskView.as_view(), name="check-objetive"),                    # POST
        path("redeem/", ExchangeDailyTaskView.as_view(), name="redeem-objetive"),               # POST
    ])),

    # Productos y Sistema de canje
    path("products/", include([
        path("", ProductView.as_view(), name="product-list"),                                   # GET
        path("redeem/", ExchangeProductView.as_view(), name="redeem-product"),                  # POST
        path("new/", ProductoCreateView.as_view(), name="new_product"),                         # POST
        path("edit/<int:id_producto>/", ProductoEditView.as_view(), name="edit_product"),       # PUT / PATCH
        path("<int:producto_id>/image/", EditProductImageView.as_view(), name="product-image"), # PATCH
    ])),

    # Categorías
    path("categories/", include([
        path("", CategoriaListView.as_view(), name="list_categories"),                          # GET
        path("new/", CategoriaCreateView.as_view(), name="new_categorie"),                      # POST
        path("edit/<int:id_categoria>/", CategoriaEditView.as_view(), name="edit_categorie"),   # PUT / PATCH
    ])),

    # Social / Ranking
    path("social/", include([
        path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),                    # GET
        path("friends/", FollowingFriendsView.as_view(), name="following-friends"),             # GET / POST
        path("ranking/", UsuarioRankingView.as_view(), name="user-ranking"),                    # GET
    ])),

    # Configuración
    path("config/", include([
        path("rewards/", RecompensasParametrosView.as_view(), name="config-rewards"),           # GET
    ])),

    # Imágenes
    path("images/", UploadImageView.as_view(), name="upload-images"),                           # POST
    path("view-image/<str:filename>/", ServeImageView.as_view(), name="view-image"),            # GET

    # Historial
    path("history/", include([
        path("redemptions/", HistoricalCanjesView.as_view(), name="history-redemptions"),       # GET
    ])),

    # Contacto
    path("contact/", ContactUsView.as_view(), name="contact-us"),                               # POST
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)