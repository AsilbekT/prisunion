from rest_framework import viewsets, status
from rest_framework.response import Response

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
import requests
from rest_framework.response import Response
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from PIL import Image
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from prisunion import settings


def standardResponse(status, message, data, pagination=None, http_status=None):
    response = {
        'status': status,
        'message': message,
        'http_status': http_status,
        'data': data
    }
    if pagination:
        response['pagination'] = pagination
    return Response(response)


def paginate_queryset(queryset, request):
    page_number = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('size', 10))

    paginator = Paginator(queryset, page_size)
    try:
        paginated_queryset = paginator.page(page_number)
    except EmptyPage:
        return [], standardResponse(status="error", message="Invalid page number.", data={})
    except PageNotAnInteger:
        return [], standardResponse(status="error", message="Page number is not an integer.", data={})

    pagination_data = {
        'total': paginator.count,
        'page_size': page_size,
        'current_page': page_number,
        'total_pages': paginator.num_pages,
        'next': paginated_queryset.has_next(),
        'previous': paginated_queryset.has_previous(),
    }

    return paginated_queryset, pagination_data


class BaseViewSet(viewsets.ModelViewSet):
    """
    A base viewset that provides default CRUD operations.
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response({
                'status': 'success',
                'message': 'Item created successfully.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED, headers=headers)
        return Response({
            'status': 'error',
            'message': 'Failed to create item.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        # Use the custom paginate_queryset function
        paginated_queryset, pagination_data = paginate_queryset(
            queryset, request)

        serializer = self.get_serializer(paginated_queryset, many=True)

        # Include the pagination_data in the response
        return standardResponse(status="success", message="Items retrieved", data=serializer.data, pagination=pagination_data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        serialized_data = serializer.data

        return standardResponse(status="success", message="Item retrieved", data=serialized_data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def details(self, request, pk=None, **kwargs):
        # "pk" is the primary key of the order
        return self.retrieve(request, **kwargs)


def send_notification(user_ids=None, message=None, all_users=False, additional_data=None):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {settings.ONESIGNAL_REST_API_KEY}"
    }

    payload = {
        "app_id": settings.ONESIGNAL_APP_ID,
        "contents": {"en": message} if message else {},
        "data": additional_data if additional_data else {}
    }

    # Targeting specific users or all users
    if all_users:
        payload["included_segments"] = ["All"]
    elif user_ids:
        payload["include_external_user_ids"] = user_ids
    else:
        raise ValueError(
            "You must specify either user_ids or set all_users=True")

    response = requests.post(
        settings.ONE_SIGNAL_NOTIFICATION_URL, headers=headers, json=payload)
    return response.json()
