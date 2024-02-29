import requests
from logs_bot.credentials import PRISUNION_ERRORS_ID, PRISUNION_STORE_ID, TELEGRAM_API_URL
from logs_bot.models import TelegramUser
from prison_market.models import Order, OrderItem
import json
from django.utils.timezone import now
from django.utils.html import escape


def send_message(chat_id, text):
    requests.post(f'{TELEGRAM_API_URL}/sendMessage',
                  data={'chat_id': chat_id, 'text': text})


def notify_new_order(order_id):
    """
    Sends a notification about a new order to the staff group with inline buttons for actions
    and formats the message using HTML in Uzbek language.

    :param order_id: The ID of the new order.
    """
    try:
        order = Order.objects.select_related(
            'prisoner', 'ordered_by').get(id=order_id)
        items = OrderItem.objects.filter(order=order).select_related('product')
    except Order.DoesNotExist:
        return

    # Constructing the order details string with improved decoration
    items_details = ""
    for item in items:
        items_details += f"<b>{item.quantity}x {item.product.name}</b> (har biri uchun <b>${item.price_at_time_of_order}</b>)\n"

    # HTML formatted message with enhanced decoration
    message = (f"🎉 <b>Yangi Buyurtma!</b>\n"
               f"Buyurtma ID: <code>{order.id}</code>\n"
               f"Jami: <b>${order.total}</b>\n"
               f"Mahbus: <i>{order.prisoner.full_name}</i> (ID: <i>{order.prisoner.identification_number}</i>)\n"
               f"Buyurtma beruvchi: <i>{order.ordered_by.full_name}</i>\n"
               f"Holati: <b>{order.get_status_display()}</b>\n"
               f"Mahsulotlar:\n{items_details}")

    chat_id = PRISUNION_STORE_ID  # Telegram group chat ID for order notifications

    # Defining inline keyboard buttons for possible actions with additional decoration
    inline_keyboard = [
        [{"text": "📦 Qabul qilish", "callback_data": f"pending_{order.id}"}],
    ]

    send_message_with_buttons(chat_id, message, inline_keyboard)


def send_message_with_buttons(chat_id, text, inline_keyboard):
    """
    Sends a message with inline buttons to a specified Telegram chat ID.
    Uses HTML formatting for the message text and includes Uzbek language decorations.

    :param chat_id: Telegram chat ID (individual or group).
    :param text: Message text, formatted as HTML.
    :param inline_keyboard: A list of lists of buttons to include in the message.
    """
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'reply_markup': json.dumps({"inline_keyboard": inline_keyboard})
    }

    response = requests.post(f'{TELEGRAM_API_URL}/sendMessage', json=payload)
    return response.json()


def send_error_to_telegram(user, error_type, description):
    """
    Sends an error report to a specified Telegram group.

    Parameters:
    - user: The user experiencing the issue. Can be a username, user ID, or any identifier.
    - error_type: A short string indicating the type of error (e.g., 'Frontend Error', 'Mobile App Crash').
    - description: Detailed description of the error or the issue the user encountered.
    """
    # Define the chat ID for your Telegram group dedicated to error logs
    chat_id = "your_telegram_group_chat_id"

    # Format the message to include all necessary details
    current_time = now().strftime('%Y-%m-%d %H:%M:%S')
    message = (f"⚠️ Error Report ⚠️\n"
               f"Time: {current_time}\n"
               f"User: {user}\n"
               f"Error Type: {error_type}\n"
               f"Description: {description}")

    # Use the send_message utility function to send the error report to the Telegram group
    send_message(chat_id, message)


def handle_message(update):
    chat_id = update['message']['chat']['id']
    from_user = update['message']['from']
    text = update.get('message', {}).get('text', '')

    register_user_if_not_exists(from_user)

    if text == "/register":
        username = update['message']['from']['username']
        TelegramUser.objects.get_or_create(
            username=username, chat_id=str(chat_id))
        send_message(chat_id, "Siz ro'yxatdan o'tdingiz.")
    elif text.startswith("/error"):
        send_message(chat_id, "Xato qayd etildi.")
    elif chat_id in [PRISUNION_ERRORS_ID, PRISUNION_STORE_ID]:
        # Handle specific logic for messages from the store or error group
        pass
    else:
        send_message(
            chat_id, "Admin bilan bog'lanish uchun, iltimos, +998990010513 raqamiga murojaat qiling.")


def handle_callback_query(update):
    callback_query = update['callback_query']
    chat_id = callback_query['message']['chat']['id']
    callback_data = callback_query['data']
    from_user = callback_query['from']
    message_id = callback_query['message']['message_id']
    register_user_if_not_exists(from_user)

    if 'pending_' in callback_data:
        new_status = 'processed'
    elif 'process_' in callback_data:
        new_status = 'delivered'
    elif 'deliver_' in callback_data:
        new_status = 'delivered'
    elif 'complete_' in callback_data:
        new_status = 'complete'
    else:
        new_status = None

    order_id = callback_data.split("_")[1] if new_status else None

    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            # Update the order status if necessary
            if new_status != order.status:
                order.status = new_status
                order.save()

            # Reconstruct the message text from order details
            items_details, message = construct_order_message(order)

            # Generate the inline keyboard based on the current status
            inline_keyboard = generate_inline_keyboard(new_status, order_id)
            # Update the Telegram message
            update_message(chat_id, message_id, message, inline_keyboard)

        except Order.DoesNotExist:
            send_message(chat_id, "Order does not exist.")
    else:
        send_message(chat_id, "Invalid action.")


def construct_order_message(order):
    items = OrderItem.objects.filter(order=order).select_related('product')
    items_details = "".join(
        [f"<b>{item.quantity}x {item.product.name}</b> (har biri uchun <b>${item.price_at_time_of_order}</b>)\n" for item in items])

    message = (f"🎉 <b>Yangi Buyurtma!</b>\n"
               f"Buyurtma ID: <code>{order.id}</code>\n"
               f"Jami: <b>${order.total}</b>\n"
               f"Mahbus: <i>{order.prisoner.full_name}</i> (ID: <i>{order.prisoner.identification_number}</i>)\n"
               f"Buyurtma beruvchi: <i>{order.ordered_by.full_name}</i>\n"
               f"Holati: <b>{order.get_status_display()}</b>\n"
               f"Mahsulotlar:\n{items_details}")
    return items_details, message


def generate_inline_keyboard(order_status, order_id):
    """
    Dynamically generates inline keyboard options based on the current status of an order.

    :param order_status: The current status of the order.
    :param order_id: The ID of the order.
    :return: Inline keyboard layout for the next possible actions.
    """
    buttons = []
    if order_status == "processed":
        buttons.append(
            [{"text": "🔄 Tayorlanmoqda", "callback_data": f"deliver_{order_id}"}])
    if order_status == "delivered":
        buttons.append(
            [{"text": "🏁 Yakunlash", "callback_data": f"complete_{order_id}"}])

    if order_status == "complete":
        buttons.append(
            [{"text": "✅ Yakunlandi", "callback_data": f"done_{order_id}"}])

    return buttons


def update_message(chat_id, message_id, text, inline_keyboard):
    """
    Sends a request to Telegram to edit a message with new text and an updated inline keyboard.
    """
    # Ensure inline_keyboard is a valid JSON object
    reply_markup = json.dumps(
        {"inline_keyboard": inline_keyboard}) if inline_keyboard else "{}"

    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup  # Ensure this is a stringified JSON
    }

    response = requests.post(
        f"{TELEGRAM_API_URL}/editMessageText", data=payload)

    return response.json()


def register_user_if_not_exists(user_info):
    """
    Registers a user if they are not already registered.

    :param user_info: Dictionary containing user information from the update.
    """
    user_id = str(user_info['id'])
    # Default to 'Unknown' if username is not present
    username = user_info.get('username', 'Unknown')
    # Check if the user is already registered
    _, created = TelegramUser.objects.get_or_create(
        username=username,
        defaults={'chat_id': user_id}
    )
    if created:
        print(f"Registered new user: {username}")
