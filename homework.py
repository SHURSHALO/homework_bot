import time
import telegram
import os
from dotenv import load_dotenv
import requests
import logging
import exceptions
from http import HTTPStatus
import sys

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens():
    """Проверяет наличие необходимых токенов в переменных окружения."""
    required_tokens = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_tokens = []

    for token in required_tokens:
        if os.getenv(token) is None:
            missing_tokens.append(token)

    if missing_tokens:
        error_message = "Следующие переменные окружения отсутствуют:"
        for token in missing_tokens:
            error_message += f"\n- {token}"
        logging.critical(error_message)
    # return True


def send_message(bot, message):
    """Отправляет сообщение в чат Телеграма."""
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if chat_id:
        try:
            bot.send_message(chat_id=chat_id, text=message)
            logging.debug('Сообщение успешно отправлено в Telegram.')
        except exceptions.SendMessageTelegramError as error:
            error_message = (
                f'Ошибка при отправке сообщения в Telegram: {error}'
            )
            logging.error(error_message)
            raise exceptions.SendMessageTelegramError(
                'Сообщение не отправлено'
            )


def get_api_answer(timestamp):
    """Получает ответ от API с информацией о статусе проверки работы."""
    payload = {'from_date': timestamp}

    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
        homework_statuses.raise_for_status()
        if homework_statuses.status_code != HTTPStatus.OK:

            raise exceptions.RequestException(
                'Ошибка при запросе к основному API:'
                f'{homework_statuses.status_code}'
            )
        return homework_statuses.json()

    except exceptions.ConnectionError as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise exceptions.ConnectionError('Ошибка соединения')

    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise exceptions.RequestError('Ошибка при запросе к API')


def check_response(response):
    """Проверяет, соответствует ли ответ от API требованиям."""
    if not isinstance(response, dict):
        raise TypeError(f'Не получен json - {response}')
    if 'homeworks' not in response:
        raise TypeError('В словаре нет домашки')
    homework_statuses = response.get('homeworks')
    if not isinstance(homework_statuses, list):
        raise TypeError('Данные по домашке не список словарей')
    if 'current_date' not in response:
        raise TypeError('Отсутствует дата текущего запроса')
    return homework_statuses


def parse_status(homework):
    """Генерирует сообщение о статусе проверки работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)

    if not homework_name:
        raise TypeError('В ответе API домашки нет ключа `homework_name`')

    if status not in HOMEWORK_VERDICTS:
        raise KeyError(f"Недокументированный статус домашней работы: {status}")

    if verdict:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()  # Проверяем наличие необходимых токенов

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    if not PRACTICUM_TOKEN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.critical("Отсутствуют обязательные переменные окружения")
        sys.exit(1)

    while True:
        try:
            response = get_api_answer(timestamp)  # Получаем ответ от API
            homework_statuses = check_response(response)  # Проверяем ответ
            for homework in homework_statuses:
                message = parse_status(
                    homework
                )  # Генерируем сообщение о статусе
                send_message(bot, message)  # Отправляем сообщение в Telegram
            time.sleep(
                RETRY_PERIOD
            )  # Ждем некоторое время перед следующим запросом

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            sys.stdout.write(message)
        finally:
            if check_response:
                timestamp = response.get('current_date')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        encoding='utf-8',
    )
    main()
