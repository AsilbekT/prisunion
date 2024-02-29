from django.shortcuts import render
from datetime import date
from django.utils.timezone import now
from django.db.models import Sum
from rest_framework import viewsets
from logs_bot.utils import notify_new_order
from prison_market.models import (
    CategoryBanner,
    Order,
    OrderItem,
    Prisoner,
    PrisonerContact,
    Product,
    ProductCategory
)

from prison_market.serializers import (
    CategoryBannerSerializer,
    OrderItemSerializer,
    OrderSerializer,
    PrisonerSerializer,
    ProductCategorySerializer,
    ProductDetailSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    PrisonerContactTokenObtainPairSerializer
)
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from prison_market.utils import BaseViewSet, paginate_queryset, standardResponse
from rest_framework.generics import CreateAPIView, RetrieveAPIView, ListAPIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer
from django.db.models import Q


class PrisonerViewSet(BaseViewSet):
    queryset = Prisoner.objects.all().order_by('-id')
    serializer_class = PrisonerSerializer


class ProductCategoryViewSet(BaseViewSet):
    queryset = ProductCategory.objects.all().order_by("-id")
    serializer_class = ProductCategorySerializer
    http_method_names = ['get']


class CategoryProductsViewSet(BaseViewSet):
    """
    A simple ViewSet for listing or retrieving products in a specific category.
    """
    serializer_class = ProductListSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action == 'retrieve':
            return ProductDetailSerializer
        else:
            return super().get_serializer_class()

    def list(self, request, category_id=None):
        queryset = Product.objects.filter(
            category_id=category_id).order_by('-id')
        paginated_queryset, pagination_data = paginate_queryset(
            queryset, request)
        print(self.serializer_class)
        serializer = self.serializer_class(
            paginated_queryset, many=True, context={'request': request})
        return standardResponse(status="success", message="Items retrieved", data=serializer.data, pagination=pagination_data)

    def retrieve(self, request, pk=None, category_id=None):
        try:
            product = Product.objects.get(pk=pk, category_id=category_id)
        except Product.DoesNotExist:
            return standardResponse(status="error", message="Product not found", data={}, pagination={})

        serializer = self.serializer_class(product)
        return standardResponse(status="success", message="Item retrieved", data=serializer.data, pagination={})


class ProductViewSet(BaseViewSet):
    queryset = Product.objects.all().order_by('-id')
    serializer_class = ProductListSerializer
    http_method_names = ['get']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def list(self, request, *args, **kwargs):

        genre_from_param = request.query_params.get('genre', None)
        trending_from_param = request.query_params.get('trending', None)
        category_from_param = request.query_params.get('category', None)

        queryset = self.get_queryset()

        filter_conditions = Q()
        if genre_from_param:
            filter_conditions &= Q(genre_id=genre_from_param)
        if trending_from_param is not None:
            trending_bool = trending_from_param.lower() in ['true', '1', 't']
            filter_conditions &= Q(is_trending=trending_bool)
        if category_from_param:
            filter_conditions &= Q(category_id=category_from_param)

        queryset = queryset.filter(filter_conditions)

        paginated_queryset, pagination_data = paginate_queryset(
            queryset, request)

        serializer = self.get_serializer(paginated_queryset, many=True)

        return standardResponse(status="success", message="Items retrieved", data=serializer.data, pagination=pagination_data)


class OrderViewSet(BaseViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.all().order_by('-id')
    serializer_class = OrderSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return OrderSerializer
        elif self.action == 'retrieve':
            return OrderSerializer
        return OrderSerializer

    def list(self, request, *args, **kwargs):
        user = request.user
        prisoner_contact_obj = PrisonerContact.objects.get(user=user.id)
        queryset = self.get_queryset().filter(
            ordered_by=prisoner_contact_obj.id)
        paginated_queryset, pagination_data = paginate_queryset(
            queryset, request)

        serializer = self.get_serializer(paginated_queryset, many=True)

        return standardResponse(status="success", message="Items retrieved", data=serializer.data, pagination=pagination_data)


class OrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrderItem.objects.all().order_by("-id")
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Still ensure this method only returns a QuerySet.
        order_id = self.kwargs.get('order_pk')
        return self.queryset.filter(order_id=order_id)

    def list(self, request, *args, **kwargs):
        # Customizing the list action to use the standardResponse.
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return standardResponse(status="success", message="Items retrieved", data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return standardResponse(status="success", message="Item retrieved", data=serializer.data)


class OrderProductView(CreateAPIView):
    serializer_class = OrderItemSerializer

    def create(self, request, *args, **kwargs):
        contact = PrisonerContact.objects.get(pk=1)

        prisoner = self.get_prisoner(request.data.get('prisoner_id'))

        # Check remaining quantity for the prisoner and get the product
        remaining_weight_today = self.get_remaining_weight(prisoner)
        product = self.get_product(request.data.get('product_id'))
        quantity = request.data.get('quantity')
        total_weight_of_order = product.weight * quantity

        # Validate total weight of the order
        if total_weight_of_order > remaining_weight_today:
            return standardResponse(status="error", message=f"Exceeds the daily weight limit. You can order up to {remaining_weight_today} kg today for this prisoner.", data={})
        if product.stock < quantity:
            return standardResponse(status="error", message="Insufficient stock for the product.", data={})

        # Create order and order item within a transaction
        with transaction.atomic():
            order = self.create_or_get_order(prisoner, contact)
            order_item = self.create_order_item(order, product, quantity)
            self.update_product_stock(product, quantity)
            self.update_order_total(order)

        # Serialize and return the order
        order_serializer = OrderSerializer(order)
        return standardResponse(status="success", message="Order placed successfully", data={'order': order_serializer.data})

    def get_prisoner(self, prisoner_id):
        # Retrieve and return the prisoner object
        return get_object_or_404(Prisoner, pk=prisoner_id)

    def authenticate_prisoner(self, request):
        return get_object_or_404(Prisoner, pk=1)

    def get_remaining_quantity(self, prisoner):
        today = date.today()
        existing_orders = Order.objects.filter(
            prisoner=prisoner,
            created_at__date=today  # Use 'created_at__date' instead of 'ordered_date__date'
        )
        total_ordered_quantity_today = sum(
            order.items.aggregate(total_quantity=Sum('quantity'))[
                'total_quantity'] or 0
            for order in existing_orders
        )
        max_quantity_today = 12
        return max_quantity_today - total_ordered_quantity_today

    def get_remaining_weight(self, prisoner):
        today = date.today()
        existing_orders = Order.objects.filter(
            prisoner=prisoner,
            created_at__date=today
        )
        total_ordered_weight_today = sum(
            order_item.product.weight * order_item.quantity
            for order in existing_orders
            for order_item in order.items.all()
        )
        max_weight_today = 12
        return max_weight_today - total_ordered_weight_today

    def get_product(self, product_id):
        return get_object_or_404(Product, pk=product_id)

    def create_or_get_order(self, prisoner, contact):
        # Adjust this method to associate the order with the contact as well
        order, created = Order.objects.get_or_create(
            prisoner=prisoner,
            ordered_by=contact,
            status='Pending'
        )
        return order

    def create_order_item(self, order, product, quantity):
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price_at_time_of_order=product.price
        )
        order.items.add(order_item)
        return order_item

    def update_product_stock(self, product, quantity):
        product.stock -= quantity
        product.save()

    def update_order_total(self, order):
        order.total = sum(
            item.price_at_time_of_order for item in order.items.all())
        order.save()


class PrisonerContactTokenObtainPairView(TokenObtainPairView):
    serializer_class = PrisonerContactTokenObtainPairSerializer


class PrisonerContactTokenRefreshView(TokenRefreshView):
    # If you need to customize the token refresh, do it here
    pass


class CreateFullOrderView(APIView):
    """
    API endpoint for creating a full order with multiple products for a prisoner by a contact.
    """

    def post(self, request, *args, **kwargs):
        prisoner_id = request.data.get('prisoner_id')
        contact_id = request.data.get('contact_id')
        products_info = request.data.get('products')

        prisoner = get_object_or_404(Prisoner, pk=prisoner_id)
        contact = get_object_or_404(PrisonerContact, pk=contact_id)

        if not products_info or not isinstance(products_info, list):
            return standardResponse(status="error", message="Invalid products list.", data={})

        with transaction.atomic():
            order = self.create_order(prisoner, contact)

            for product_info in products_info:
                product_id = product_info.get('product_id')
                quantity = product_info.get('quantity')

                if not product_id or not quantity:
                    # Rollback transaction and return error response
                    transaction.set_rollback(True)
                    return standardResponse(status="error", message="Product ID and quantity are required for each item.", data={})

                product = get_object_or_404(Product, pk=product_id)
                if product.stock < quantity:
                    transaction.set_rollback(True)
                    return standardResponse(status="error", message=f"Insufficient stock for product ID {product_id}.", data={})

                self.create_order_item(order, product, quantity)

            self.update_order_total(order)

        serializer = OrderSerializer(order)
        notify_new_order(order.id)
        return standardResponse(status="success", message="Order placed successfully", data=serializer.data)

    def create_order(self, prisoner, contact):
        # Create a new order
        order = Order.objects.create(
            prisoner=prisoner,
            ordered_by=contact,
            status='Pending'
        )
        return order

    def create_order_item(self, order, product, quantity):
        # Create an order item and associate it with the order
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price_at_time_of_order=product.price
        )
        order.items.add(order_item)
        product.stock -= quantity
        product.save()

    def update_order_total(self, order):
        # Recalculate the order total based on the order items
        order.total = sum(
            item.quantity * item.price_at_time_of_order for item in order.items.all()
        )
        order.save()


class CategoryBannerListView(BaseViewSet):
    queryset = CategoryBanner.objects.all().order_by('-id')
    serializer_class = CategoryBannerSerializer


class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(recipient=user).order_by('-created_at')
