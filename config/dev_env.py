import os

from config.common import MARTIN

SETTINGS = {
        'ADMIN_ID': MARTIN,
        'TELEGRAM_BOT_TOKEN': os.environ.get('TELEGRAM_BOT_TOKEN'),
}
