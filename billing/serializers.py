from rest_framework import serializers

from prisoner_contact_auth.utils import ensure_https
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
