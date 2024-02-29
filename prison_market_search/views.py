from django.db.models import Q
from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from prison_market.models import Product, ProductCategory
from prison_market.serializers import ProductListSerializer
from rest_framework.views import APIView
from prison_market.utils import standardResponse, paginate_queryset


class AdvancedSearch(APIView):
    def get(self, request):
        # Search and filtering parameters
        query = request.GET.get('q', '')
        category = request.GET.get('category', None)
        min_weight = request.GET.get('min_weight', None)
        max_weight = request.GET.get('max_weight', None)
        min_price = request.GET.get('min_price', None)
        max_price = request.GET.get('max_price', None)

        # Construct the base query
        products_query = Q(name__icontains=query)

        # Filter by category if provided
        if category:
            # Assuming categories are separated by commas
            categories = category.split(',')
            categories_query = Q(category__name__in=categories)
            products_query = products_query & categories_query

        # Filter by weight if provided
        if min_weight:
            products_query = products_query & Q(weight__gte=min_weight)
        if max_weight:
            products_query = products_query & Q(weight__lte=max_weight)

        # Filter by price if provided
        if min_price:
            products_query = products_query & Q(price__gte=min_price)
        if max_price:
            products_query = products_query & Q(price__lte=max_price)

        try:
            # Execute the query
            products = Product.objects.filter(
                products_query).order_by("-id").distinct()
        except ValidationError as e:
            # Handle any potential validation errors, e.g., invalid decimal format
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        paginated_queryset, pagination_data = paginate_queryset(
            products, request)

        serializer = ProductListSerializer(paginated_queryset, many=True)

        return standardResponse(status="success", message="Items retrieved", data=serializer.data, pagination=pagination_data)
