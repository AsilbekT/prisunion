from django.contrib import admin
from .models import CategoryBanner, PrisonerContact, Prison, Prisoner, Product, Order, OrderItem, ProductCategory
from django.utils.html import format_html
from django.contrib import admin
from django_json_widget.widgets import JSONEditorWidget
from django.contrib.postgres.fields import JSONField
from django.db import models

from .models import Notification


@admin.register(Prison)
class PrisonAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location', 'capacity',
                    'security_level', 'contact_info')
    search_fields = ('name', 'location')


@admin.register(Prisoner)
class PrisonerAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'identification_number',
                    'prison', 'cell_number', 'date_of_birth')
    search_fields = ('full_name', 'identification_number', 'cell_number')
    list_filter = ('prison', 'date_of_birth')


@admin.register(PrisonerContact)
class PrisonerContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'prisoner', 'relationship',
                    'phone_number', 'is_approved')
    search_fields = ('full_name', 'prisoner__full_name', 'relationship')
    list_filter = ('relationship', 'is_approved')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'category', 'stock')
    search_fields = ('name', 'description', 'category')
    list_filter = ('category',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'prisoner', 'ordered_by', 'created_at',
                    'status', 'total', 'payment_status')
    list_filter = ('status', 'created_at', 'payment_status')
    search_fields = ('prisoner__full_name',
                     'ordered_by__user__username', 'status')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price_at_time_of_order')
    search_fields = ('order__id', 'product__name')


class CategoryBannerInline(admin.TabularInline):
    model = CategoryBanner
    extra = 1  # Specifies the number of empty forms to display
    fields = ('image', 'title', 'description', 'link')


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_tag')
    search_fields = ['name']
    inlines = [CategoryBannerInline]  # Add the inline

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;"/>', obj.image.url)
        return "-"
    image_tag.short_description = 'Image'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'message', 'all_users')
    list_filter = ('all_users',)
    search_fields = ('message',)
