class SendMessageTelegramError(Exception):
    """Сообщение не отправляется."""

    pass


class RequestError(Exception):
    """Ошибка при запросе к API."""

    pass


class AbsentAPI(Exception):
    """Не хватает глобаной переменной."""

    pass
