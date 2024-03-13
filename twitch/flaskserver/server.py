import importlib

import gevent

from twitch.flaskserver.internaloauth import InternalOauth
from twitch.util.config import Config
from twitch.util.logging import LoggingClass


class FlaskConfig(Config):
    http_host = '0.0.0.0'
    http_port = 7575

    proxy_fix = False
    event_sub = False
    use_internal_logging = True
    add_twitch_to_context = True
    views = []
    flask_app = ''


class FlaskServer(LoggingClass):
    def __init__(self, client, config: FlaskConfig = None):
        super(FlaskServer, self).__init__()

        self.config = config or FlaskConfig()
        self._client = client

        self.app = None

        self._wsgi_server = None
        self._greenlet = None
        self._alternate_app = None
        if self.config.flask_app:
            self._alternate_app = importlib.import_module(self.config.flask_app)
        self.setup_flask(self._alternate_app)

    def setup_flask(self, _app=None, temp=False):
        try:
            from flask import Flask, current_app
            from gevent.pywsgi import WSGIServer
            from werkzeug.middleware.proxy_fix import ProxyFix
        except ImportError:
            self.log.warning('Failed to start HTTP Server, Flask is not installed')
            return

        self.app = _app or Flask("Twitch-FlaskServer")
        self._wsgi_server = WSGIServer((self.config.http_host, self.config.http_port), self.app,
                                       log=self.log if self.config.use_internal_logging else None)

        if not temp:
            if self.config.event_sub:
                # TODO: Impl eventsub in flaskserver
                if self._client.es:
                    self.log.info("Not starting event sub for flask server, already enabled in EventSub Websocket!")
                else:
                    pass
                    # self.app.register_blueprint(EventSub)

            if self.config.proxy_fix:
                # TODO: allow configuration for proxyfix
                self.app.wsgi_app = ProxyFix(self.app.wsgi_app)

        if self.config.add_twitch_to_context or temp:
            with self.app.app_context():
                current_app.flaskserver = self
                current_app.client = self._client

        if self.config.views:
            for view in self.config.views:
                _dir = view.split(".")
                bp = _dir.pop()
                try:
                    package = importlib.import_module(".".join(_dir))
                    self.app.register_blueprint(getattr(package, bp))
                    self.log.info(f"Adding plugin module at path {view}")
                except ImportError and AttributeError:
                    self.log.warning(f'Cannot import {view}')

        # TODO: maybe not add this when its not needed? :)
        self.app.register_blueprint(InternalOauth(self._client, self._client.config))

    def shutdown(self):
        self.log.info("Shutting down Flask Server")
        self._wsgi_server.stop()
        return

    def serve(self):
        self._greenlet = gevent.spawn(self._wsgi_server.serve_forever)
        self.log.info(f'Starting Flask server bound to {self.config.http_host}:{self.config.http_port}')