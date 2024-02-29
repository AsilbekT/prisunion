from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import requests

from logs_bot.credentials import PRISUNION_ERRORS_ID, PRISUNION_STORE_ID, TELEGRAM_API_URL, TELEGRAM_BOT_TOKEN, URL
from logs_bot.utils import handle_callback_query, handle_message, send_message, update_message
from prison_market.models import Order
from .models import TelegramUser
import json


def setwebhook(request):
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={URL}")

    return JsonResponse(response.json())


@csrf_exempt
@require_POST
def webhook(request):
    update = json.loads(request.body.decode('utf-8'))
    if 'callback_query' in update:
        handle_callback_query(update)
    elif 'message' in update:
        handle_message(update)

    return JsonResponse({'ok': True})
