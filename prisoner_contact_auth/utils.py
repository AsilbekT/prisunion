import requests
from django.conf import settings


def get_eskiz_auth_token():
    url = 'https://notify.eskiz.uz/api/auth/login'
    headers = {'Content-Type': 'application/json'}
    payload = {
        'email': settings.ESKIZ_EMAIL,
        'password': settings.ESKIZ_PASSWORD
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json()['data']['token']
    else:
        # Handle error (log or raise exception)
        return None


def send_sms_via_eskiz(to_number, message):
    token = get_eskiz_auth_token()
    if token is None:
        return False  # or handle error appropriately

    url = 'https://notify.eskiz.uz/api/message/sms/send'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'mobile_phone': to_number,
        'message': message,
        'from': 4546
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return True  # SMS sent successfully
    else:
        # Handle error (log or raise exception)
        return False


def ensure_https(url):
    if not url.startswith('https://'):
        return url.replace('http://', 'https://')
    return url
