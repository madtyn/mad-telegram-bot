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


def get_bot_app_name():
    """
    Returns the bot app name for Heroku deployment
    :return: the bot app name string
    """
    return VALUES['BOT_APP_NAME']


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