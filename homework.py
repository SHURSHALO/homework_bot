import os
import time
import logging
from typing import Dict, List, Any

from http import HTTPStatus
from dotenv import load_dotenv
import telegram
import requests
from requests import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS: Dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens() -> bool:
    """Проверяет наличие необходимых токенов в переменных окружения."""
    required_tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if not all(required_tokens):
        logging.critical('Не хватает глобаной переменной')
        raise exceptions.AbsentAPI('Не хватает глобаной переменной')

    return True


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в чат Телеграма."""
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    try:
        bot.send_message(chat_id=chat_id, text=message)
        logging.debug('Сообщение успешно отправлено в Telegram.')
    except Exception as error:
        error_message = f'Ошибка при отправке сообщения в Telegram: {error}'
        logging.error(error_message)
        raise exceptions.SendMessageTelegramError('Сообщение не отправлено')


def get_api_answer(timestamp: int) -> Dict[str, Any]:
    """Получает ответ от API с информацией о статусе проверки работы."""
    payload = {'from_date': timestamp}

    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
        homework_statuses.raise_for_status()
        if homework_statuses.status_code != HTTPStatus.OK:
            raise requests.RequestException(
                'Ошибка при соединении HTTPStatus not ОК: '
                f'{homework_statuses.status_code}'
            )
        return homework_statuses.json()

    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise exceptions.RequestError('Ошибка при запросе к API')


def check_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Проверяет, соответствует ли ответ от API требованиям."""
    if not isinstance(response, dict):
        raise TypeError(f'Не получен json - {response}')
    if 'homeworks' not in response:
        raise TypeError('В словаре нет домашки')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError('Данные по домашке не список словарей')
    if 'current_date' not in response:
        raise TypeError('Отсутствует дата текущего запроса')
    return homework[0]


def parse_status(homework: Dict[str, Any]) -> str:
    """Генерирует сообщение о статусе проверки работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)

    if not homework_name:
        raise TypeError('В ответе API домашки нет ключа `homework_name`')

    if status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Недокументированный статус домашней работы: {status}')

    if not verdict:
        raise KeyError('Вердикт не опознан')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        timestamp = int(time.time())

        while True:
            try:
                response = get_api_answer(timestamp)
                homework_statuses = check_response(response)
                message = parse_status(homework_statuses)
                send_message(bot, message)

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error(message)

            finally:
                if check_response:
                    timestamp = response.get('current_date')
                time.sleep(RETRY_PERIOD)
    else:
        time.sleep(RETRY_PERIOD)
        main()


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        encoding='utf-8',
    )
    main()
