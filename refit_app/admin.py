from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from rangefilter.filters import DateRangeFilter
from refit_app.models import (
    User, Imagen, Producto, Categoria, ProductoImagen, ProductoCategoria,
    Pasos, Canje, ObjetivoDiario, UsuarioObjetivoDiario, Parametro, Transaccion
)

# ==========================================================================
# ADMIN – ReFit App
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Configuración de administración para los modelos de ReFit.
#              Se definen qué campos mostrar, bloquear y buscar.
# ==========================================================================

admin.site.unregister(Group)

# --------------------------------------------------------------------------
# Administración de usuarios
# --------------------------------------------------------------------------
@admin.action(description="Restablecer racha a cero para los usuarios seleccionados")
def resetear_racha_usuarios(modeladmin, request, queryset):
    queryset.update(racha=0)

@admin.action(description="Eliminar usuarios seleccionados")
def eliminar_usuarios(modeladmin, request, queryset):
    queryset.delete()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Datos personales", {"fields": ("email", "nombre", "apellidos", "genero", "fecha_nacimiento")}),
        ("Referencias", {"fields": ("codigo_referido", "fk_usuario_referente")}),
        ("Estadísticas", {"fields": ("objetivo_diario", "racha", "pasos_totales", "monedas_actuales")}),
        ("Sistema", {"fields": ("fecha_registro", "last_login", "fecha_modificacion"), "classes": ("collapse",)}),
    )
    readonly_fields = ("fecha_registro", "last_login", "fecha_modificacion")
    list_display = ("email", "nombre", "apellidos", "monedas_actuales", "pasos_totales", "racha")
    search_fields = ("email", "nombre", "apellidos", "codigo_referido", "fk_usuario_referente__email")
    list_filter = ("genero", ("fecha_registro", DateRangeFilter))
    actions = [resetear_racha_usuarios, eliminar_usuarios]
    list_select_related = ("fk_usuario_referente",)

    def has_add_permission(self, request):
        return False

# --------------------------------------------------------------------------
# Administración de imágenes
# --------------------------------------------------------------------------
@admin.register(Imagen)
class ImagenAdmin(admin.ModelAdmin):
    list_display = ("pk_imagenes", "uuid", "extension", "fecha_creacion")
    search_fields = ("uuid",)
    readonly_fields = ("fecha_creacion",)

# --------------------------------------------------------------------------
# Administración de productos
# --------------------------------------------------------------------------
@admin.action(description="Marcar productos seleccionados como destacados")
def marcar_productos_destacados(modeladmin, request, queryset):
    queryset.update(destacado=True)

@admin.action(description="Activar productos seleccionados")
def activar_productos(modeladmin, request, queryset):
    queryset.update(disponible=True)

@admin.action(description="Desactivar productos seleccionados")
def desactivar_productos(modeladmin, request, queryset):
    queryset.update(disponible=False)

@admin.action(description="Eliminar productos seleccionados")
def eliminar_productos(modeladmin, request, queryset):
    queryset.delete()

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("pk_productos", "nombre", "precio_monedas", "disponible", "destacado", "fecha_creacion")
    list_filter = ("disponible", "destacado", ("fecha_creacion", DateRangeFilter))
    search_fields = ("nombre", "descripcion")
    readonly_fields = ("fecha_creacion",)
    actions = [marcar_productos_destacados, activar_productos, desactivar_productos, eliminar_productos]

# --------------------------------------------------------------------------
# Administración de categorías
# --------------------------------------------------------------------------
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("pk_categorias", "nombre", "codigo", "fecha_creacion")
    search_fields = ("nombre", "codigo")
    list_filter = ("fecha_creacion",)
    readonly_fields = ("fecha_creacion",)

# --------------------------------------------------------------------------
# Administración de producto-imágenes
# --------------------------------------------------------------------------
@admin.register(ProductoImagen)
class ProductoImagenAdmin(admin.ModelAdmin):
    list_display = ("id", "fk_productos", "fk_imagenes", "fecha_creacion")
    list_select_related = ("fk_productos", "fk_imagenes")
    readonly_fields = ("fecha_creacion",)

# --------------------------------------------------------------------------
# Administración de producto-categorías
# --------------------------------------------------------------------------
@admin.register(ProductoCategoria)
class ProductoCategoriaAdmin(admin.ModelAdmin):
    list_display = ("pk_productos_categorias", "fk_productos", "fk_categorias", "fecha_creacion")
    readonly_fields = ("fecha_creacion",)
    list_select_related = ("fk_productos", "fk_categorias")

# --------------------------------------------------------------------------
# Administración de pasos
# --------------------------------------------------------------------------
@admin.register(Pasos)
class PasoAdmin(admin.ModelAdmin):
    list_display = ("pk_pasos", "fk_usuarios", "fecha", "pasos", "fecha_creacion")
    list_filter = (("fecha", DateRangeFilter),)
    search_fields = ("fk_usuarios__email", "fk_usuarios__nombre")
    readonly_fields = ("fecha_creacion",)
    list_select_related = ("fk_usuarios",)

# --------------------------------------------------------------------------
# Administración de canjes
# --------------------------------------------------------------------------
@admin.register(Canje)
class CanjeAdmin(admin.ModelAdmin):
    list_display = ("pk_canjes", "fk_usuarios", "fk_productos", "monto", "fecha")
    list_filter = (("fecha", DateRangeFilter),)
    search_fields = ("fk_usuarios__email", "fk_productos__nombre")
    readonly_fields = ("fecha",)
    list_select_related = ("fk_usuarios", "fk_productos")

# --------------------------------------------------------------------------
# Administración de objetivos diarios
# --------------------------------------------------------------------------
@admin.register(ObjetivoDiario)
class ObjetivoDiarioAdmin(admin.ModelAdmin):
    list_display = ("pk_objetivos_diarios", "nombre", "premio", "fecha_creacion")
    readonly_fields = ("fecha_creacion",)
    search_fields = ("nombre", "descripcion")

# --------------------------------------------------------------------------
# Administración de usuario-objetivos diarios
# --------------------------------------------------------------------------
@admin.register(UsuarioObjetivoDiario)
class UsuarioObjetivoDiarioAdmin(admin.ModelAdmin):
    list_display = (
        "pk_usuarios_objetivos_diarios", "fk_usuarios", "fk_objetivos_diarios",
        "fecha_completado", "fecha_canjeado", "fecha_creacion", "fecha_modificacion"
    )
    list_filter = (("fecha_completado", DateRangeFilter), ("fecha_canjeado", DateRangeFilter))
    search_fields = ("fk_usuarios__email", "fk_objetivos_diarios__nombre")
    readonly_fields = ("fecha_creacion", "fecha_modificacion")
    list_select_related = ("fk_usuarios", "fk_objetivos_diarios")

# --------------------------------------------------------------------------
# Administración de parámetros
# --------------------------------------------------------------------------
@admin.register(Parametro)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ("pk_parametros", "codigo", "valor", "fecha_creacion")
    search_fields = ("codigo",)
    readonly_fields = ("fecha_creacion",)

# --------------------------------------------------------------------------
# Administración de transacciones
# --------------------------------------------------------------------------
@admin.register(Transaccion)
class TransaccionAdmin(admin.ModelAdmin):
    list_display = ("pk_transacciones", "pk_usuarios", "uuid", "monto", "tipo", "fecha_creacion")
    search_fields = ("uuid", "pk_usuarios__email", "pk_usuarios__nombre")
    readonly_fields = ("fecha_creacion",)
    list_filter = (("fecha_creacion", DateRangeFilter), "tipo")
    list_select_related = ("pk_usuarios",)
