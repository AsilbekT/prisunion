from django.contrib import admin
from .models import Transaction
from django.utils.html import format_html


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_id', 'phone_number', 'amount', 'status')
    search_fields = ('transaction_id', 'amount')
