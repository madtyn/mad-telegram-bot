"""
Alternative:

from datetime import datetime
import pytz

SPAIN_TIMEZONE = pytz.timezone('Europe/Madrid')

"""

import pytz
import tzlocal


USER_TZ = pytz.timezone('Europe/Madrid')
SERVER_TZ = tzlocal.get_localzone()
