from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import hashlib
import json
import requests
from requests.auth import HTTPBasicAuth
from django.core.cache import cache
from billing.serializers import TransactionSerializer
from prison_market.models import Order
from prison_market.utils import standardResponse
from prisunion import settings
from .models import Transaction
import logging
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


logger = logging.getLogger(__name__)


class BasePaymentView(APIView):
    """
    Base view for common payment functionalities.
    """

    def get_access_token(self):
        access_token = cache.get('access_token')
        if access_token is not None:
            return access_token

        try:
            response = requests.post(
                settings.OAUTH_TOKEN_URL,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': f'Basic {settings.BASIC_AUTH}'
                },
                data={
                    'grant_type': 'password',
                    'username': settings.OAUTH_USERNAME,
                    'password': settings.OAUTH_PASSWORD
                }
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            access_token = response.json().get('access_token')
            # Default to 1 hour if not provided
            expires_in = response.json().get('expires_in', 17560)

            # Store the token in cache for the duration of the token's validity
            cache.set('access_token', access_token, timeout=expires_in)
            return access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching access token: {e}")
            raise

    def generate_hash_key(self, *args):
        # Concatenate args into a single string, encode it to bytes, and hash it
        data_string = ''.join(args)
        return hashlib.new('SHA3-256', data_string.encode()).hexdigest()


class PayHoldTransactionView(BasePaymentView):
    def post(self, request, *args, **kwargs):
        required_fields = ['pan', 'expire', 'amount', 'orderId']
        missing_fields = [
            field for field in required_fields if field not in request.data]
        if missing_fields:
            error_message = f"Missing fields: {', '.join(missing_fields)}"
            return Response({'errorMessage': error_message}, status=status.HTTP_400_BAD_REQUEST)

        access_token = self.get_access_token()
        orderId = request.data.get('orderId')

        hash_key = self.generate_hash_key(
            settings.OAUTH_USERNAME,
            request.data.get('pan'),
            settings.SALT_HOLD,
            str(request.data.get('amount')),
            settings.CLIENT_ID
        )

        payload = {
            "pan": request.data.get('pan'),
            "expire": request.data.get('expire'),
            "merchantId": settings.MERCHANT_ID,
            "amount": request.data.get('amount'),
            "currency": settings.CURRENCY,
            "hashKey": hash_key
        }

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.post(
            settings.API_URL_HOLD, data=json.dumps(payload), headers=headers)

        if response.status_code == 200:
            response_data = response.json().get('data', {})
            transaction_id = response_data.get('transactionId')
            phone = response_data.get('phone')

            transaction, created = Transaction.objects.get_or_create(
                transaction_id=transaction_id,
                defaults={
                    'phone_number': phone,
                    'amount': request.data.get('amount'),
                    'status': 'pending'
                }
            )
            order = Order.objects.filter(id=orderId).first()
            if order:
                order.transaction = transaction
                order.save()

            return Response({
                'transactionId': transaction_id,
                'phone': phone
            }, status=status.HTTP_201_CREATED)

        else:
            error_message = response.json().get('errorMessage', 'An error occurred')
            return Response({'errorMessage': error_message}, status=response.status_code)


class PayTransactionView(BasePaymentView):
    def post(self, request, *args, **kwargs):
        required_fields = ['transactionId', 'smsCode']
        missing_fields = [
            field for field in required_fields if field not in request.data]
        if missing_fields:
            error_message = f"Missing fields: {', '.join(missing_fields)}"
            return Response({'errorMessage': error_message}, status=status.HTTP_400_BAD_REQUEST)

        access_token = self.get_access_token()
        transaction_id = request.data.get('transactionId')

        hash_key = self.generate_hash_key(
            settings.CLIENT_ID,
            settings.SALT_PAY,
            request.data.get('smsCode'),
            request.data.get('transactionId')
        )
        payload = {
            "transactionId": transaction_id,
            "smsCode": request.data.get('smsCode'),
            "hashKey": hash_key
        }

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Make the payment request to the OFB API
        response = requests.post(
            settings.API_URL_PAY, data=json.dumps(payload), headers=headers)

        if response.status_code == 200:
            response_data = response.json().get('data', {})
            phone = response_data.get('phone', '')
            transaction = Transaction.objects.filter(
                transaction_id=transaction_id).first()
            if transaction:
                transaction.status = "completed"
                transaction.phone_number = phone
                transaction.save()

            order = Order.objects.filter(transaction=transaction).first()
            if order:
                order.payment_status = "completed"
                order.save()

            # Returning a successful response
            return Response({
                'transactionId': transaction_id,
                'status': 'completed',
                'phone': phone,
                "qrCodeUrl": response_data['qrCodeUrl']
            }, status=status.HTTP_200_OK)

        else:
            error_message = response.json().get(
                'errorMessage', 'An error occurred during the payment process')

            # Returning an error response
            return Response({
                'errorMessage': error_message
            }, status=response.status_code)


class CheckStatusView(BasePaymentView):
    def get(self, request, transaction_id, *args, **kwargs):
        access_token = self.get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}

        url = f"{settings.API_URL_CHECK_STATUS}/{transaction_id}"

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            # Optionally update the transaction status in the database
            Transaction.objects.filter(transaction_id=transaction_id).update(
                status=response.json().get('status', 'Unknown')
            )

        return Response(response.json(), status=response.status_code)


class TransactionView(viewsets.ReadOnlyModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter transactions by the logged-in user
        return Transaction.objects.filter(user=self.request.user).order_by("-id")

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
