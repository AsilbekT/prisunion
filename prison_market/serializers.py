from rest_framework import serializers
from prisoner_contact_auth.utils import ensure_https
from .models import CategoryBanner, Prisoner, Product, Order, OrderItem, ProductCategory
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from .models import PrisonerContact
from django.contrib.auth import authenticate
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Notification


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'


class PrisonerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prisoner
        fields = '__all__'


class ProductListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'weight', 'image', 'category']

    def get_image(self, obj):
        """Method to get the image field value."""
        if obj.image:
            request = self.context.get('request')
            image_url = obj.image.url
            if request:
                return ensure_https(request.build_absolute_uri(image_url))
            else:
                return ensure_https(image_url)
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        prisoner = PrisonerSerializer(read_only=True)
        ordered_by = serializers.PrimaryKeyRelatedField(read_only=True)
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = OrderItem
        product = ProductListSerializer(read_only=True)
        fields = '__all__'


class PrisonerContactTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # The default result (access and refresh tokens)
        data = super().validate(attrs)

        # Authenticate the user based on username & password
        user = authenticate(
            username=attrs['username'], password=attrs['password'])

        # Check if the authenticated user is a PrisonerContact
        if not PrisonerContact.objects.filter(user=user).exists():
            raise AuthenticationFailed(
                'No active account found with the given credentials')

        # Include the user's type in the token payload (optional)
        data['user_type'] = 'prisoner_contact'

        # Include any other custom claims here

        return data


class CreateOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['prisoner', 'ordered_by', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order


class CategoryBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryBanner
        fields = ['id', 'category', 'image', 'title', 'description', 'link']

    # Adding a method to get the full URL for the image
    def to_representation(self, instance):
        # Original representation
        representation = super().to_representation(instance)
        request = self.context.get('request')

        # Ensure the image URL is absolute and uses HTTPS
        if instance.image and request:
            representation['image'] = ensure_https(
                request.build_absolute_uri(instance.image.url))

        # Dynamically construct the category link
        if instance.category_id and request:
            # Get the base URL and remove trailing slash
            base_url = request.build_absolute_uri('/')[:-1]
            category_link = f"{base_url}/productcategories/{instance.category_id}/products/"
            representation['link'] = ensure_https(category_link)
        else:
            # Optionally handle the case where the request or category_id is not available
            representation['link'] = None

        return representation


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'title', 'message', 'created_at', 'read']
