from rest_framework import generics, views, status
from rest_framework.response import Response
from django.db import transaction
from django.contrib.auth.models import User
from rest_framework.exceptions import APIException
from prison_market.models import PrisonerContact
from .serializers import PrisonerContactSerializer, PrisonerContactTokenObtainPairSerializer
from prisoner_contact_auth.utils import send_sms_via_eskiz
import random
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from prison_market.utils import standardResponse
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import IntegrityError
from rest_framework.permissions import IsAuthenticated


class PrisonerContactTokenObtainPairView(TokenObtainPairView):
    serializer_class = PrisonerContactTokenObtainPairSerializer


class PrisonerContactTokenRefreshView(TokenRefreshView):
    # If you need to customize the token refresh, do it here
    pass


class PrisonerContactView(views.APIView):
    def post(self, request, *args, **kwargs):
        # This method now handles both creation and update using phone_number
        return self.handle_request(request)

    def handle_request(self, request):
        with transaction.atomic():
            phone_number = request.data.get('phone_number')
            if not phone_number:
                return standardResponse(status="error", message="Phone number is required.", data={}, http_status=400)

            try:
                prisoner_contact = PrisonerContact.objects.get(
                    phone_number=phone_number)
                serializer = PrisonerContactSerializer(
                    prisoner_contact, data=request.data, partial=True, context={'request': request})
                operation = "update"
            except PrisonerContact.DoesNotExist:
                serializer = PrisonerContactSerializer(data=request.data)
                operation = "create"

            if serializer.is_valid():
                username = serializer.validated_data.get('username')
                password = serializer.validated_data.get('password')
                # Create or update user here as needed
                user, created = User.objects.get_or_create(
                    username=username)
                if created or not user.check_password(password):
                    user.set_password(password)
                    user.save()

                prisoner_contact = serializer.save()
                prisoner_contact.user = user
                prisoner_contact.save()
                # Only generate tokens if a user is associated
                if user:
                    refresh = RefreshToken.for_user(user)
                    tokens = {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                    response_data = {"tokens": tokens}
                else:
                    response_data = {}

                response_data.update(serializer.data)
                return standardResponse(status="success", message=f"Prisoner contact {operation}d successfully.", data=response_data)

            return standardResponse(status="error", message="Validation failed.", data=serializer.errors)


class GetPrisonerContactView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        print(request)
        user = request.user
        print(user)
        try:
            prisoner_contact = PrisonerContact.objects.get(user=user)
            serializer = PrisonerContactSerializer(prisoner_contact)

            return standardResponse(status="success", message='Prisoner contact retrieved successfully.', data=serializer.data)
        except PrisonerContact.DoesNotExist:
            standardResponse(
                status="error", message='Prisoner contact not found.', data=[], http_status=404)

    def post(self, request, *args, **kwargs):
        # This method now handles both creation and update using phone_number
        return self.handle_request(request)

    def handle_request(self, request):
        with transaction.atomic():
            phone_number = request.data.get('phone_number')
            if not phone_number:
                return standardResponse(status="error", message="Phone number is required.", data={}, http_status=400)

            try:
                prisoner_contact = PrisonerContact.objects.get(
                    phone_number=phone_number)
                serializer = PrisonerContactSerializer(
                    prisoner_contact, data=request.data, partial=True, context={'request': request})
                operation = "update"
            except PrisonerContact.DoesNotExist:
                serializer = PrisonerContactSerializer(data=request.data)
                operation = "create"

            if serializer.is_valid():
                username = serializer.validated_data.get('username')
                password = serializer.validated_data.get('password')
                # Create or update user here as needed
                user, created = User.objects.get_or_create(
                    username=username)
                if created or not user.check_password(password):
                    user.set_password(password)
                    user.save()

                prisoner_contact = serializer.save()
                prisoner_contact.user = user
                prisoner_contact.save()
                # Only generate tokens if a user is associated
                if user:
                    refresh = RefreshToken.for_user(user)
                    tokens = {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                    response_data = {"tokens": tokens}
                else:
                    response_data = {}

                response_data.update(serializer.data)
                return standardResponse(status="success", message=f"Prisoner contact {operation}d successfully.", data=response_data)

            return standardResponse(status="error", message="Validation failed.", data=serializer.errors)


class PrisonerContactLoginView(views.APIView):
    throttle_scope = 'prisoner_contact_login'

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        verification_code = random.randint(1000, 9999)
        message = f"Your login verification code is: {verification_code}"

        if send_sms_via_eskiz(phone_number, message):
            PrisonerContact.objects.filter(phone_number=phone_number).update(
                phone_verification_code=str(verification_code))
            return standardResponse(status="success", message="Verification code sent", data={})
        else:
            return standardResponse(status="error", message="Failed to send verification code", data={}, http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPrisonerContactView(views.APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')

        try:
            prisoner_contact = PrisonerContact.objects.get(
                phone_number=phone_number, phone_verification_code=code)
            prisoner_contact.phone_verified = True
            prisoner_contact.phone_verification_code = ''
            prisoner_contact.save()
            return standardResponse(status="success", message="Phone number verified successfully", data={})
        except PrisonerContact.DoesNotExist:
            return standardResponse(status="error", message="Invalid phone number or verification code", data={})


class ResendVerificationCodeView(views.APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        try:
            prisoner_contact = PrisonerContact.objects.get(
                phone_number=phone_number)
            verification_code = random.randint(1000, 9999)
            prisoner_contact.phone_verification_code = str(verification_code)
            prisoner_contact.save()

            message = f"Your new verification code is: {verification_code}"
            if send_sms_via_eskiz(phone_number, message):
                return Response({'status': 'success', 'message': 'Verification code resent successfully.'}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'error', 'message': 'Failed to send verification code.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except PrisonerContact.DoesNotExist:
            return Response({'status': 'error', 'message': 'Prisoner contact not found.'}, status=status.HTTP_404_NOT_FOUND)


class RequestLoginCodeView(views.APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')

        if not phone_number:
            return Response({'status': 'error', 'message': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        verification_code = random.randint(1000, 9999)
        message = f"Your login verification code is: {verification_code}"

        try:
            prisoner_contact, created = PrisonerContact.objects.get_or_create(
                phone_number=phone_number,
                defaults={'phone_verification_code': str(verification_code)}
            )
            prisoner_contact.phone_verification_code = str(verification_code)
            prisoner_contact.save()

            if send_sms_via_eskiz(phone_number, message):
                response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
                return Response({
                    'status': 'success',
                    'message': 'Verification code sent.',
                    'created': created
                }, status=response_status)
            else:
                return Response({'status': 'error', 'message': 'Failed to send verification code.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except IntegrityError as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyLoginCodeView(views.APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        verification_code = request.data.get('code')

        if not phone_number or not verification_code:
            # Using standardResponse for error
            return standardResponse(status="error", message="Phone number and code are required.", data={}, http_status=status.HTTP_400_BAD_REQUEST)

        try:
            prisoner_contact = PrisonerContact.objects.get(
                phone_number=phone_number, phone_verification_code=verification_code)

            prisoner_contact.phone_verified = True
            prisoner_contact.phone_verification_code = ''
            prisoner_contact.save()
            if not prisoner_contact.user:
                data = {
                    'refresh': None,
                    'access': None,
                }
            # Generate JWT token for authenticated user
            else:
                user = prisoner_contact.user
                refresh = RefreshToken.for_user(user)
                data = {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            # Using standardResponse for success
            return standardResponse(status="success", message="Phone number verified successfully.", data=data)
        except PrisonerContact.DoesNotExist:
            # Using standardResponse for error
            return standardResponse(status="error", message="Invalid phone number or verification code.", data={}, http_status=status.HTTP_404_NOT_FOUND)
