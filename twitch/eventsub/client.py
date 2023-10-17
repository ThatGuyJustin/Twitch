import ssl
from json import JSONDecodeError

import gevent
from websocket import WebSocketTimeoutException, WebSocketConnectionClosedException

from twitch.util.leakybucket import LeakyBucket, LeakyBucketException
from twitch.util.logging import LoggingClass
from twitch.util.websocket import Websocket

try:
    import ujson as json
except ImportError:
    import json

# TODO:
#   Dynamic mapping
#   HeartBeat


class EventSubClient(LoggingClass):
    def __init__(self, client=None):
        super(EventSubClient, self).__init__()

        # TODO: CONFIG
        self.max_reconnects = 1
        self.remember_past_events = 15
        # TODO: CONFIG END

        self.ws = None
        self.ws_event = gevent.event.Event()  # noqa

        self.session_id = None
        self.shutting_down = False
        self.reconnects = 0

        self._client = client
        self._gateway_url = "wss://eventsub.wss.twitch.tv/ws"
        self._last_events = LeakyBucket(self.remember_past_events)

    def on_open(self):
        self.log.info('WS Opened')

    def on_close(self, code=None, reason=None):
        # if self._heartbeat_task:
        #     self.log.info('WS Closed: killing heartbeater')
        #     try:
        #         self._heartbeat_task.kill(timeout=5)
        #     except TimeoutError:
        #         self.log.info('Heartbeater kill timeout')

        # If we're quitting, just break out of here
        if self.shutting_down:
            self.log.info('WS Closed: shutting down')
            return

        self.reconnects += 1
        self._last_events.clean()


        self.log.info('WS Closed:{}{} ({})'.format(' [{}]'.format(code) if code else '', ' {}'.format(reason) if reason else '', self.reconnects))

        if self.max_reconnects and self.reconnects > self.max_reconnects:
            raise Exception('Failed to reconnect after {} attempts, giving up'.format(self.max_reconnects))

        # TODO handle logic on non resumes/reconnects
        self.connect_and_run()

    def on_error(self, error):
        if isinstance(error, KeyboardInterrupt):
            self.shutting_down = True
            self.ws_event.set()
        if isinstance(error, WebSocketTimeoutException):
            return self.log.error('Websocket connection has timed out. An upstream connection issue is likely present.')
        if not isinstance(error, WebSocketConnectionClosedException):
            raise Exception('WS received error: {}'.format(error))

    def on_message(self, msg):
        try:
            data = json.loads(msg)
        except JSONDecodeError:
            self.log.exception('Failed to parse ws message: ')
            return

        # Check if msg was already sent
        _mid = data.get('metadata', {}).get('message_id', None)
        if not _mid:
            self.log.warning(f"Websocket message does not contain metadata:\n{data}")
            return

        try:
            self._last_events.add(_mid, throw=True)
        except LeakyBucketException:
            self.log.warning(f"Duplicate websocket message: {_mid}")
            return

        self.log.info(data)

    def connect_and_run(self, gateway_url=None):
        if gateway_url:
            self._gateway_url = gateway_url

        self.log.info('Opening websocket connection to URL `%s`', self._gateway_url)
        self.ws = Websocket(self._gateway_url)
        self.ws.emitter.on('on_open', self.on_open)
        self.ws.emitter.on('on_error', self.on_error)
        self.ws.emitter.on('on_close', self.on_close)
        self.ws.emitter.on('on_message', self.on_message)
        self.ws.run_forever(sslopt={'cert_reqs': ssl.CERT_NONE})

    def run(self):
        gevent.spawn(self.connect_and_run)
        self.ws_event.wait()
