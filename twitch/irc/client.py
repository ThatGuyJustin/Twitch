import ssl

import gevent
import gevent.event

from twitch.types.irc import IRCRawMessage
from twitch.util.leakybucket import LeakyBucket
from twitch.util.logging import LoggingClass
from twitch.util.websocket import Websocket
from websocket import WebSocketTimeoutException, WebSocketConnectionClosedException


class IRCClient(LoggingClass):
    def __init__(self, client):
        super(IRCClient, self).__init__()

        # TODO: CONFIG
        self.max_reconnects = 25
        self.remember_past_events = 15
        self.capabilities = ['membership', 'tags', 'commands']
        # TODO: CONFIG END

        self._events = client.events

        self.irc: Websocket = None  # noqa
        self.greenlet = None

        self.shutting_down = False
        self.reconnects = 0

        self._client = client
        self._token = None
        self._nick = None
        self._irc_url = "wss://irc-ws.chat.twitch.tv"
        # self._irc_status = "STARTING"
        self._last_events = LeakyBucket(self.remember_past_events)

    def on_close(self, code=None, reason=None):
        self._events.emit("CHAT_WS_CLOSED")

        # If we're quitting, just break out of here
        if self.shutting_down:
            self.log.info('IRC WS Closed: shutting down')
            return

        # TODO: Find another way given _irc_status can be removed
        # if self._irc_status != "RECONNECT_REQUEST":
        #     self.reconnects += 1
        #     self._last_events.clean()
        #     self.log.info('IRC WS Closed:{}{} ({})'.format(' [{}]'.format(code) if code else '',
        #                                                    ' {}'.format(reason) if reason else '', self.reconnects))
        #
        #     if self.max_reconnects and self.reconnects > self.max_reconnects:
        #         raise Exception('Failed to reconnect after {} attempts, giving up'.format(self.max_reconnects))

        # TODO handle logic on non resumes/reconnects
        self.connect_and_run()

    def on_open(self):
        self._events.emit("CHAT_WS_OPEN")
        # self._irc_status = "OPENED"
        self.log.info('WS Opened')

        for x in self.capabilities:
            self.send(f"CAP REQ :twitch.tv/{x}")

        self.send(f"PASS oauth:{self._token}")
        self.send(f"NICK {self._nick}")
        self._events.emit("CHAT_READY")

    def send(self, data):
        self.log.debug(f"Sending message: {data}")
        return self.irc.send(data)

    def on_error(self, error):
        if isinstance(error, KeyboardInterrupt):
            self.shutting_down = True
        if isinstance(error, WebSocketTimeoutException):
            return self.log.error('Websocket connection has timed out. An upstream connection issue is likely present.')
        if not isinstance(error, WebSocketConnectionClosedException):
            raise Exception('WS received error: {}'.format(error))

    def shutdown(self):
        if self.irc:
            self.log.warning("Graceful shutdown initiated")
            self.irc.shutting_down = True
            self.irc.close()

    def on_message(self, msg):
        for _msg in msg.split("\r\n"):
            self._events.emit("IRC_WS_RAW", _msg)
            e = IRCRawMessage.from_raw(msg)

            if e.command == "PING":
                return self.on_ping(e)
            else:
                # IF ITS NOT PING
                pass

    def on_ping(self, msg: IRCRawMessage):
        self.send(f"PONG {msg.parameters}")

    def connect_and_run(self):
        self.log.info('Opening irc connection to URL `%s`', self._irc_url)
        self.irc = Websocket(self._irc_url)
        self.irc.emitter.on('on_open', self.on_open)
        self.irc.emitter.on('on_error', self.on_error)
        self.irc.emitter.on('on_close', self.on_close)
        self.irc.emitter.on('on_message', self.on_message)
        self.irc.run_forever(sslopt={'cert_reqs': ssl.CERT_NONE})

    def run(self):
        self.greenlet = gevent.spawn(self.connect_and_run)