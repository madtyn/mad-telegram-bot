import logging


class TimedOutFilter(logging.Filter):
    def filter(self, record):
        if "Error while getting Updates: Timed out" in record.getMessage():
            return False
        return True
