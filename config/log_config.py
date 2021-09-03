import os
import time
from functools import wraps, partial

from config.common import deploy_server, production
from config.timezone import USER_TZ, SERVER_TZ
from config.version import version
import logging
from logging.handlers import SMTPHandler, TimedRotatingFileHandler
from logging import Formatter

from datetime import datetime
from common.utils.filters import TimedOutFilter

LOG_MESSAGE_FORMAT = '%(asctime)s - ({0}) %(levelname)s - %(name)s - %(message)s'

version_num = version()
LOGFILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'log',
                            'mtgabot.log')

logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('chardet.charsetprober').setLevel(logging.WARNING)

if production():
    logging.getLogger().addHandler(logging.NullHandler())  # Fix duplicate lines

EMAIL_WARNING = 35

LOG_LEVELS = {
    10: logging.DEBUG,
    20: logging.INFO,
    30: logging.WARNING,
    35: EMAIL_WARNING,
    40: logging.ERROR,
    50: logging.CRITICAL,
}

LOG_LABELS = {
    10: 'DEBUG',
    20: 'INFO',
    30: 'WARNING',
    35: 'EMAIL_WARNING',
    40: 'ERROR',
    50: 'CRITICAL',
}


def logged(input_logger):
    """
    Decorates a handler for logging its entering
    and exit using an logger parameter
    :param input_logger: the logger to use
    :return: the logged function
    """
    def logging_decorator(my_handler):
        @wraps(my_handler)
        def wrapped(*args, **kwargs):
            start = time.time()
            input_logger.info('<=== {}'.format(my_handler.__name__))
            result = my_handler(*args, **kwargs)
            input_logger.info(f'===> {my_handler.__name__}: <{time.time() - start}>')
            return result
        return wrapped
    return logging_decorator


def my_timezone_time(*args):
    return SERVER_TZ.localize(datetime.now()).astimezone(USER_TZ).timetuple()


formatter = Formatter(LOG_MESSAGE_FORMAT.format(version_num))
formatter.converter = my_timezone_time

handlers = []
fh = TimedRotatingFileHandler(LOGFILE_PATH, when='midnight')
fh.setFormatter(formatter)
fh.setLevel(logging.DEBUG)
handlers.append(fh)

if deploy_server():
    mh = SMTPHandler(mailhost=("smtp.gmail.com", 587),
                     fromaddr="martin.torre.castro@gmail.com",
                     toaddrs="madtyn@gmail.com",
                     subject=u"MTGA Bot error!",
                     credentials=("martin.torre.castro@gmail.com", os.environ.get('GMAIL_PASSWORD')),
                     secure=())
    mh.setFormatter(formatter)
    mh.setLevel(EMAIL_WARNING)
    handlers.append(mh)

ch = logging.StreamHandler()
ch.setFormatter(formatter)
ch.setLevel(logging.INFO)
handlers.append(ch)


def getLogger(name):
    """
    Return a logger for the file
    :param name: the file name
    :return: a logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addFilter(TimedOutFilter())
    logger.maildev = partial(logger.log, EMAIL_WARNING)

    for h in handlers:
        logger.addHandler(h)

    return logger


def log_level(input_level=None):
    """
    Sets dynamically the log level to a new value
    :param input_level:  the new log level value as an int
    """
    current_log_level = handlers[0].level
    if input_level:
        current_log_level = new_level = LOG_LEVELS.get(input_level, input_level)
        for h in handlers:
            h.setLevel(new_level)
    return f'{LOG_LABELS[current_log_level]}({current_log_level})'


if __name__ == '__main__':
    logger_ = getLogger(__name__)
    try:
        raise Exception()
    except Exception as e:
        logger_.exception('Unhandled Exception')
        logger_.error('an error line')
        logger_.debug('a debug line')
