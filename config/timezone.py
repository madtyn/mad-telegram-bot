"""
Alternative:

from datetime import datetime
import pytz

SPAIN_TIMEZONE = pytz.timezone('Europe/Madrid')

"""

import dateutil.tz as tz

USER_TZ = tz.gettz('Europe/Madrid')
SERVER_TZ = tz.tzlocal()
