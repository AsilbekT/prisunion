from django.urls import path
from .views import (
    GetPrisonerContactView,
    PrisonerContactView,
    PrisonerContactTokenObtainPairView,
    PrisonerContactTokenRefreshView,
    RequestLoginCodeView,
    ResendVerificationCodeView,
    VerifyLoginCodeView,
    VerifyPrisonerContactView,
    PrisonerContactLoginView,
)

urlpatterns = [
    path('api/token/', PrisonerContactTokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('api/token/refresh/', PrisonerContactTokenRefreshView.as_view(),
         name='token_refresh'),
    path('api/create_prisoner_contact/',
         PrisonerContactView.as_view(), name='create_prisoner_contact'),
    path('api/get_prisoner_contact/',
         GetPrisonerContactView.as_view(), name='get_prisoner_contact'),
    path('api/verify_prisoner_contact/', VerifyPrisonerContactView.as_view(),
         name='verify_prisoner_contact'),
    path('api/prisoner_contact_login/', PrisonerContactLoginView.as_view(),
         name='prisoner_contact_login/'),

    path('api/contact/login/request/',
         RequestLoginCodeView.as_view(), name='request_login_code'),
    path('api/contact/login/verify/',
         VerifyLoginCodeView.as_view(), name='verify_login_code'),
    path('api/contact/resend_code/', ResendVerificationCodeView.as_view(),
         name='resend_verification_code'),
]
