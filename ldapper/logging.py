
class ProxyLogger(object):
    """
    This class provides a wrapper for the standard Python logging
    facilities.  Handlers do not store their messages.  Their messages
    flush immediately to whereever they are intended to go.

    ProxyLogger proxies those received messages along, but also stores them,
    so that they can be retrieved and enumerated later.
    """

    def __init__(self, logger):
        self._messages = []
        self.logger = logger

    def get_messages(self):
        return self._messages

    def flush(self):
        """Clear all messages and return them afterwards."""
        messages = self._messages
        self._messages = []
        return messages

    def warning(self, msg):
        self._messages.append(("WARNING", msg))
        self.logger.warning(msg)

    def info(self, msg):
        self._messages.append(("INFO", msg))
        self.logger.info(msg)

    def error(self, msg):
        self._messages.append(("ERROR", msg))
        self.logger.error(msg)

    def debug(self, msg):
        self._messages.append(("DEBUG", msg))
        self.logger.debug(msg)

    def has_errors(self):
        return any(et == 'ERROR' for et, _ in self._messages)

    def has_warnings(self):
        return any(et == 'WARNING' for et, _ in self._messages)
