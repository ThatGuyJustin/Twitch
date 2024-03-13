import gevent
import gevent.event

from twitch.irc.client import IRCClient
from twitch.api.client import APIClient
from twitch.eventsub.client import EventSubClient
from twitch.util.config import Config
from twitch.util.emitter import Emitter
from twitch.util.logging import LoggingClass


class ClientConfig(Config):
    """
    Configuration for the `Client`.

    Attributes
    ----------
    client_id : str
        The token for the twitch development app
    client_secret : str
        The secret for the twitch development app
    log_level : str
        The logging level to use.
    """

    client_id = ''
    client_secret = ''

    log_level = 'info'
    log_unknown_events = False


class Client(LoggingClass):
    """
    Class representing the base entry point that should be used in almost all
    implementation cases. This class wraps the functionality of both the REST API
    (`disco.api.client.APIClient`) and the realtime gateway API
    (`disco.gateway.client.GatewayClient`).

    Parameters
    ----------
    config : `ClientConfig`
        Configuration for this client instance.

    Attributes
    ----------
    config : `ClientConfig`
        The runtime configuration for this client.
    events : `Emitter`
        An emitter which emits EventSub events.
    api : `APIClient`
        The API client.
    es : `EventSubClient`
        The EventSub client.
    irc : `IRCClient`
        The IRC client.
    flask : `FlaskServer`
        The Flask Server.
    cli : `CLI`
        The CLI.
    """

    def __init__(self, config):
        super(Client, self).__init__()
        self.config = config

        self.events = Emitter()

        self.api = APIClient()

        self.es = None
        self.irc = None
        self.flask = None
        self.cli = None

        self.running = gevent.event.Event()

    def shutdown(self):
        self.log.info("Graceful shutdown initiated")

        if self.es:
            self.es.shutdown()
        if self.irc:
            self.irc.shutdown()
        if self.flask:
            self.flask.shutdown()

        self.running.set()

    def start(self):
        """
        Main Client "Eventloop" a blocking request to keep the process running
        """
        # TODO: Start things here maybe

        if self.es:
            self.es.run()
        if self.irc:
            self.irc.run()
        if self.flask:
            self.flask.serve()

        self.running.wait()

    def run(self):
        """
        Run the client (e.g. the `Client`) in a new greenlet. (Non-Blocking)
        """
        return gevent.spawn(self.start)

    def run_forever(self):
        """
        Run the client (e.g. the `Client`) in the current greenlet. (blocking)
        """
        return self.start()
