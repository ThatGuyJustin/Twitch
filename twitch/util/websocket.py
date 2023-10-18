import websocket

from twitch.util.emitter import Emitter
from twitch.util.logging import LoggingClass


class Websocket(LoggingClass, websocket.WebSocketApp):
    """
    A utility class which wraps the functionality of: class:`websocket.WebSocketApp`
    changing its behavior to better conform with standard style across twitch.

    The major difference comes with the move from callback functions, to all
    events being piped into a single emitter.
    """
    def __init__(self, *args, **kwargs):
        LoggingClass.__init__(self)
        websocket.setdefaulttimeout(25)
        websocket.WebSocketApp.__init__(self, *args, **kwargs)

        self.emitter = Emitter()

        # Hack to get events to emit
        for var in self.__dict__.keys():
            # TODO: May not work
            if not var.startswith('on_'):
                continue

            setattr(self, var, var)

    def _callback(self, callback, *args):
        if not callback:
            return

        self.emitter.emit(callback, *args)
