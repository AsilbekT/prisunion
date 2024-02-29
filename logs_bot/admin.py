from django.contrib import admin

from logs_bot.models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'chat_id', 'registered_on')
    search_fields = ('username', 'chat_id')
    list_filter = ('registered_on',)
