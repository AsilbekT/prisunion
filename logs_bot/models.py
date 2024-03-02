from django.db import models


class TelegramUser(models.Model):
    username = models.CharField(max_length=100, unique=True)
    chat_id = models.CharField(max_length=100, unique=True)
    registered_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
