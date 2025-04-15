import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from django.shortcuts import get_object_or_404

from refit_app.models import Producto, Categoria, ProductoCategoria, Canje, Imagen, ProductoImagen
from refit_app.serializers import ProductSerializer, CategoriaSerializer

logger = logging.getLogger(__name__)

# ============================================================================
# PRODUCT VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Vistas API relacionadas con productos y su canje.
# ============================================================================
# --------------------------------------------------------------------------
# Registro de Producto y Categoría
# --------------------------------------------------------------------------
class ProductoCreateView(APIView):
    """
    Permite a un administrador registrar un nuevo producto.
    Requiere: { "nombre": "Nombre del producto", "descripcion": "Descripción del producto",
              "precio_monedas": 100, "codigo_categoria": "CATEGORIA1" }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Registra un nuevo producto en la tienda.
        Se requiere un código de categoría válido.
        """
        data = request.data.copy()
        codigo_categoria = data.get('codigo_categoria')

        if not codigo_categoria:
            return Response({'error': 'Debe proporcionar un código de categoría'}, status=400)

        try:
            categoria = Categoria.objects.get(codigo=codigo_categoria)
        except Categoria.DoesNotExist:
            return Response({'error': 'Categoría no encontrada'}, status=404)

        # Crear el producto
        data['fk_categorias'] = categoria.pk_categorias
        serializer = ProductSerializer(data=data)

        if serializer.is_valid():
            producto = serializer.save()

            # Crear la relación Producto-Categoría
            ProductoCategoria.objects.create(fk_productos=producto, fk_categorias=categoria)

            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
class CategoriaCreateView(APIView):
    """
    Permite a un administrador registrar una nueva categoría.
    Requiere: { "nombre": "Nombre de la categoría", "codigo": "CATEGORIA1" }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Registra una nueva categoría en la tienda.
        Se requiere un código único para la categoría.
        """
        serializer = CategoriaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
# --------------------------------------------------------------------------
# Listado de productos y categorias disponibles
# --------------------------------------------------------------------------
class ProductView(APIView):
    """
    Devuelve todos los productos disponibles para canje en la tienda.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve todos los productos disponibles para canje.
        """
        productos = Producto.objects.filter(disponible=True).order_by('-fecha_creacion')
        serializer = ProductSerializer(productos, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
class CategoriaListView(APIView):
    """
    Devuelve todas las categorías disponibles en la tienda.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Devuelve todas las categorías disponibles.
        """
        categorias = Categoria.objects.all().order_by('-fecha_creacion')
        serializer = CategoriaSerializer(categorias, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

# --------------------------------------------------------------------------
# Editar producto o categoria existente (Admin)
# --------------------------------------------------------------------------
class ProductoEditView(APIView):
    """
    Permite a un administrador editar un producto existente.
    Requiere: { "nombre": "Nuevo nombre", "descripcion": "Nueva descripción",
              "precio_monedas": 150, "disponible": true }
    """
    permission_classes = [IsAdminUser]

    def put(self, request, id_producto):
        """
        Edita un producto existente en la tienda.
        Se requiere un ID de producto válido.
        """
        producto = get_object_or_404(Producto, pk=id_producto)
        serializer = ProductSerializer(producto, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def patch(self, request, id_producto):
        """
        Edita parcialmente un producto existente en la tienda.
        Se requiere un ID de producto válido.
        """
        producto = get_object_or_404(Producto, pk=id_producto)
        serializer = ProductSerializer(producto, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
class EditProductImageView(APIView):
    """
    Permite a un administrador asociar una imagen a un producto.
    Requiere: { "imagen_id": 5 }
    """
    permission_classes = [IsAdminUser]

    def patch(self, request, producto_id):
        """
        Asocia una imagen a un producto existente.
        Se requiere un ID de producto y un ID de imagen válidos.
        """
        imagen_id = request.data.get("imagen_id")

        if not imagen_id:
            return Response({"error": "Falta el ID de la imagen."}, status=HTTP_400_BAD_REQUEST)

        try:
            producto = Producto.objects.get(pk_productos=producto_id)
        except Producto.DoesNotExist:
            return Response({"error": "Producto no encontrado."}, status=HTTP_400_BAD_REQUEST)

        try:
            imagen = Imagen.objects.get(pk_imagenes=imagen_id)
        except Imagen.DoesNotExist:
            return Response({"error": "Imagen no encontrada."}, status=HTTP_400_BAD_REQUEST)

        # Asignar como imagen destacada (campo directo del producto)
        producto.imagen_destacada = imagen
        producto.save()

        # Registrar relación en tabla intermedia PRODUCTOS_IMAGENES
        ProductoImagen.objects.get_or_create(
            fk_productos=producto,
            fk_imagenes=imagen
        )

        return Response({
            "detail": "Imagen del producto actualizada correctamente.",
            "image_url": f"/media/{imagen.uuid}{imagen.extension}"
        }, status=HTTP_200_OK)
    
class CategoriaEditView(APIView):
    """
    Permite a un administrador editar una categoría existente.
    Requiere: { "nombre": "Nuevo nombre", "codigo": "NUEVO_CATEGORIA" }
    """
    permission_classes = [IsAdminUser]

    def put(self, request, id_categoria):
        """
        Edita una categoría existente en la tienda.
        Se requiere un ID de categoría válido.
        """
        categoria = get_object_or_404(Categoria, pk=id_categoria)
        serializer = CategoriaSerializer(categoria, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def patch(self, request, id_categoria):
        """
        Edita parcialmente una categoría existente en la tienda.
        Se requiere un ID de categoría válido.
        """
        categoria = get_object_or_404(Categoria, pk=id_categoria)
        serializer = CategoriaSerializer(categoria, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
# --------------------------------------------------------------------------
# Canjeo de producto por monedas
# --------------------------------------------------------------------------
class ExchangeProductView(APIView):
    """
    Permite al usuario canjear un producto a cambio de monedas.
    Valida disponibilidad de monedas y producto.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Permite al usuario canjear un producto a cambio de monedas.
        Se requiere un ID de producto válido.
        """
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"error": "Falta el ID del producto."}, status=HTTP_400_BAD_REQUEST)

        producto = get_object_or_404(Producto, pk=product_id)

        if not producto.disponible:
            return Response({"error": "El producto no está disponible."}, status=HTTP_400_BAD_REQUEST)

        if request.user.monedas_actuales < producto.precio_monedas:
            return Response({"error": "Monedas insuficientes."}, status=HTTP_400_BAD_REQUEST)

        # Registrar canje en tabla CANJES
        Canje.objects.create(
            fk_usuarios=request.user,
            fk_productos=producto,
            monto=producto.precio_monedas
        )

        request.user.monedas_actuales -= producto.precio_monedas
        request.user.save()

        return Response({"message": "Producto canjeado con éxito."}, status=HTTP_200_OK)
