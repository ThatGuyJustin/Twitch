import ssl
import time
from json import JSONDecodeError

import gevent
import gevent.event

from websocket import WebSocketTimeoutException, WebSocketConnectionClosedException

from twitch.eventsub.events import EventSubEvent
from twitch.util.leakybucket import LeakyBucket, LeakyBucketException
from twitch.util.logging import LoggingClass
from twitch.util.websocket import Websocket

try:
    import ujson as json
except ImportError:
    import json

class EventSubClient(LoggingClass):
    def __init__(self, client=None, gateway_url=None):
        super(EventSubClient, self).__init__()

        # TODO: CONFIG
        self.max_reconnects = 25
        self.remember_past_events = 15
        # TODO: CONFIG END

        self._events = client.events

        self.ws = None
        self.ws_event = gevent.event.Event()

        self.session_id = None
        self.shutting_down = False
        self.reconnects = 0

        self._client = client
        self._gateway_url = "wss://eventsub.wss.twitch.tv/ws" if not gateway_url else gateway_url
        self._keepalive_timeout_seconds = None
        self._heartbeat_task = None
        self._last_event_sent = None
        self._ws_status = "STARTING"
        self._last_events = LeakyBucket(self.remember_past_events)

    def on_open(self):
        self._ws_status = "OPENED"
        self.log.info('WS Opened')

    def on_close(self, code=None, reason=None):
        self._events.emit("WEBSOCKET_CLOSED")
        if self._heartbeat_task:
            self.log.info('WS Closed: killing heartbeater')
            try:
                self._heartbeat_task.kill(timeout=5)
            except TimeoutError:
                self.log.info('Heartbeater kill timeout')

        # If we're quitting, just break out of here
        if self.shutting_down:
            self.log.info('WS Closed: shutting down')
            return

        if self._ws_status != "RECONNECT_REQUEST":
            self.reconnects += 1
            self._last_events.clean()
            self.log.info('WS Closed:{}{} ({})'.format(' [{}]'.format(code) if code else '', ' {}'.format(reason) if reason else '', self.reconnects))

            if self.max_reconnects and self.reconnects > self.max_reconnects:
                raise Exception('Failed to reconnect after {} attempts, giving up'.format(self.max_reconnects))

        # TODO handle logic on non resumes/reconnects
        self.connect_and_run()

    def on_error(self, error):
        print(error)
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
        _type = data.get('metadata', {}).get("message_type", None)
        if not _mid:
            self.log.warning(f"Websocket message does not contain required metadata:\n{data}")
            return

        try:
            self._last_events.add(_mid, throw=True)
        except LeakyBucketException:
            self.log.warning(f"Duplicate websocket message: {_mid}")
            return

        self._last_event_sent = time.time()
        if "session_" in _type:
            method = getattr(self, f"on_tw_{_type.split('session_')[1]}", None)
            if not method:
                self.log.error(f"Websocket session event not mapped:\n{data}")
            else:
                method(data.get('payload', {}))
        else:
            obj = EventSubEvent.from_dispatch(self._client, data)
            self.log.debug('EventSubClient.handle_dispatch %s', obj.__class__.__name__)
            self._client.events.emit(obj.__class__.__name__, obj)

    def on_tw_welcome(self, data):
        obj = data.get("session", {})
        self.session_id = obj['id']
        self._keepalive_timeout_seconds = obj['keepalive_timeout_seconds']
        self._heartbeat_task = gevent.spawn(self.heartbeat_task)
        self._ws_status = "CONNECTED"
        self._events.emit("WEBSOCKET_READY")

    def on_tw_keepalive(self, data):
        self.log.debug('Got keepalive event')

    def on_tw_reconnect(self, data):
        self.log.debug("Got requested by Twitch to reconnect")
        obj = data.get("session", {})
        if obj.get('reconnect_url', None):
            self._gateway_url = obj['reconnect_url']
        self._keepalive_timeout_seconds = None
        self._ws_status = "RECONNECT_REQUEST"
        self._events.emit("WEBSOCKET_RECONNECT")
        # maybe code
        self.ws.close()


    def heartbeat_task(self):
        self.log.debug("Twitch EventSub Heartbeat Listener started")
        while True:
            if (self._keepalive_timeout_seconds is not None) and (time.time() - self._last_event_sent) > self._keepalive_timeout_seconds:
                self.log.warning(f'Twitch failed to send an event in {self._keepalive_timeout_seconds}s, Forcing a reconnect') # noqa
                # maybe need code?
                self.ws.close()
            # Dynamicly set mayhaps
            gevent.sleep(5)


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
