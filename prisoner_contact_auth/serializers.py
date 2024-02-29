# serializers.py

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from prison_market.models import PrisonerContact
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError

from prisoner_contact_auth.utils import ensure_https


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

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Check if the authenticated user is a PrisonerContact
        if not PrisonerContact.objects.filter(user=user).exists():
            raise AuthenticationFailed('The user is not a prisoner contact')

        # Add custom claims
        token['user_type'] = 'prisoner_contact'
        # You can add more custom data based on your user model
        # token['is_staff'] = user.is_staff

        return token


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password']
        extra_kwargs = {'password': {'write_only': True}}


class PrisonerContactSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True)
    picture = serializers.SerializerMethodField()

    class Meta:
        model = PrisonerContact
        # Includes 'username' and 'password' as write-only fields plus all other model fields
        fields = '__all__'
        extra_kwargs = {
            # Remove unique validator to allow update operations
            'phone_number': {'validators': []},
        }

    def create(self, validated_data):
        # Pop user-related data if present (should be handled in the view)
        validated_data.pop('username', None)
        validated_data.pop('password', None)

        # Create the PrisonerContact instance
        prisoner_contact = super().create(validated_data)
        return prisoner_contact

    def update(self, instance, validated_data):
        # Pop user-related data if present (should not update user details here)
        validated_data.pop('username', None)
        validated_data.pop('password', None)

        # Update the PrisonerContact instance
        return super().update(instance, validated_data)

    def get_picture(self, obj):
        if obj.picture:  # Assuming 'picture' is the field name in your model
            request = self.context.get('request')
            picture_url = obj.picture.url
            if request is not None:
                return ensure_https(request.build_absolute_uri(picture_url))
            else:
                # If no request in context, return relative URL or absolute URL using settings if applicable
                return picture_url
        return None
