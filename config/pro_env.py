import os

from config.common import MARTIN

SETTINGS = {
        'BOT_APP_NAME': 'mtga-telegram-bot',
        'ADMIN_ID': MARTIN,
        'TELEGRAM_BOT_TOKEN': os.environ.get('TELEGRAM_BOT_TOKEN'),
}
