import os
from config.common import COMMON_SETTINGS, get_active_env
from config.log_config import getLogger


if get_active_env() == 'pro':
    from config.pro_env import SETTINGS
else:
    from config.dev_env import SETTINGS


logger = getLogger(__name__)


def get_config_path():
    """
    Returns the directory for the config
    :return: the config directory path
    """
    return os.path.dirname(__file__)


# We must remove this VALUES and use an env variable-based config
VALUES = {}
VALUES.update(COMMON_SETTINGS)

VALUES.update(SETTINGS)


def get_bot_url():
    """
    Returns the bot app name for Heroku deployment
    :return: the bot app name string
    """
    host = ''
    if VALUES.get('HOST'):
        host = f"{VALUES.get('HOST')}"
    elif VALUES.get('BOT_APP_NAME'):
        host = f"{VALUES.get('BOT_APP_NAME')}.herokuapp.com"

    return f'https://{host}/{get_bot_token()}'


def get_bot_token():
    """
    Returns the configured bot token
    :return: the bot token for the active environment
    """
    return VALUES['TELEGRAM_BOT_TOKEN']


def get_allowed_users():
    """
    Returns the allowed users' ids for this bot
    :return: the ids
    """
    return VALUES['LIST_OF_ADMINS']


def get_admin_id():
    return VALUES['ADMIN_ID']


def get_pinned_message():
    if VALUES.get('PINNED_MESSAGE', '').strip():
        return f"Para cualquier duda mira el mensaje anclado, por favor:\n\t {VALUES['PINNED_MESSAGE']} "
    return ''
