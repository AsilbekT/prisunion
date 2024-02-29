from django.urls import path
from .views import CheckStatusView, PayHoldTransactionView, PayTransactionView

urlpatterns = [
    path('pay-hold/', PayHoldTransactionView.as_view(), name='pay-hold'),
    path('pay-transaction/', PayTransactionView.as_view(), name='pay-transaction'),
    path('check-status/<str:transaction_id>/',
         CheckStatusView.as_view(), name='check-status'),
]
