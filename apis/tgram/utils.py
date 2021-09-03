from functools import wraps

from config.common import MARTIN
from config.environments import get_admin_id, get_allowed_users

from telegram.error import TimedOut, NetworkError

from config.log_config import getLogger

logger = getLogger(__name__)

main_bot = None
BOT_TIMEOUT = 7
MAX_ATTEMPTS = 10


def set_bot(input_bot):
    global main_bot
    main_bot = input_bot


def get_bot():
    global main_bot
    return main_bot


def reply_chat(chat_id, message, msg_edit=None, *args, **kwargs):
    """
    Replies in a chat_id with a message
    :param message: the text for sending
    :param chat_id: the chat id
    :param msg_edit: reference message for editing and not repyling to it
    :param args: the args list
    :param kwargs: the extra named arguments for sending the message
    :return:
    """
    exit_condition = False
    attempts = 0

    while not exit_condition:
        if get_bot() and chat_id:
            try:
                if msg_edit:
                    result = get_bot().edit_message_text(message, chat_id=chat_id,
                                                         message_id=msg_edit.message_id,
                                                         timeout=BOT_TIMEOUT, *args, **kwargs)
                else:
                    result = get_bot().send_message(chat_id, message,
                                                    timeout=BOT_TIMEOUT, *args, **kwargs)
                exit_condition = True
                return result
            except (TimedOut, NetworkError):
                attempts += 1
                if attempts > MAX_ATTEMPTS:
                    exit_condition = True


def admin_forward(text, update):
    """
    Sends a text to the admin with a message as an exception cause
    """
    reply_chat(get_admin_id(), text)
    get_bot().forward_message(get_admin_id(), update.effective_chat.id, update.message.message_id)


def admin_reply(text, *args, **kwargs):
    """
    Sends a text to the admin
    """
    reply_chat(get_admin_id(), text, *args, **kwargs)


def dev_reply(text, *args, **kwargs):
    """
    Sends a text to the developer
    """
    reply_chat(MARTIN, text, *args, **kwargs)


def reply_func(update):
    """
    Returns a new reply function which replies
    to this update effective chat from this bot
    :param update: the update info from Telegram
    :return: a new reply function
    """
    def wrapped(message, *args, **kwargs):
        chat_id = update.effective_chat.id
        return reply_chat(chat_id, message, *args, **kwargs)

    return wrapped


def restricted(input_logger):
    def restrict_decorator(my_handler, *args, **kwargs):
        """
        Decorates a handler for restricting its use
        :param my_handler: the handler to be restricted
        :return: the restricted handler
        """
        @wraps(my_handler)
        def wrapped(bot, update, *args, **kwargs):
            user_id, user_name = update.effective_user.id, update.effective_user.first_name
            if user_id not in get_allowed_users():
                input_logger.warning("Acceso no autorizado para el usuario {} con id {}".format(user_name, user_id))
                return
            input_logger.info('Entrada: {} '.format(my_handler.__name__))
            result = my_handler(bot, update, *args, **kwargs)
            input_logger.info('Salida: {} '.format(my_handler.__name__))
            return result
        return wrapped
    return restrict_decorator



