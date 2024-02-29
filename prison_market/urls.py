# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryBannerListView,
    CreateFullOrderView,
    NotificationListView,
    OrderProductView,
    PrisonerViewSet,
    ProductCategoryViewSet,
    ProductViewSet,
    OrderViewSet,
    OrderItemViewSet,
    CategoryProductsViewSet
)

router = DefaultRouter()
router.register(r'prisoners', PrisonerViewSet)
router.register(r'products', ProductViewSet)
router.register(r'banners', CategoryBannerListView)
router.register(r'productcategories',
                ProductCategoryViewSet, basename='category')
router.register(r'productcategories/(?P<category_id>\d+)/products',
                CategoryProductsViewSet, basename='category-products')
router.register(r'orders', OrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('order-product/',
         OrderProductView.as_view(), name='order-product'),
    path('create-full-order/', CreateFullOrderView.as_view(),
         name='create-full-order'),
    path('orders/<int:order_pk>/items/',
         OrderItemViewSet.as_view({'get': 'list'}), name='order-items'),
    path('orders/<int:order_pk>/items/<int:pk>/',
         OrderItemViewSet.as_view({'get': 'retrieve'}), name='order-item-detail'),
    path('notifications/', NotificationListView.as_view(),
         name='notification-list'),
]
