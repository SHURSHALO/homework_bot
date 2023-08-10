class SendMessageTelegramError(Exception):
    """Сообщение не отправляется."""

    pass


class ConnectionError(Exception):
    """Ошибка соединения."""

    pass


class RequestError(Exception):
    """Ошибка при запросе к API."""

    pass


class RequestException(Exception):
    """Ошибка при запросе к основному API."""

    pass
