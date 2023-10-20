import gevent
import gevent.event

from twitch.eventsub.client import EventSubClient
from twitch.util.config import Config
from twitch.util.emitter import Emitter
from twitch.util.logging import LoggingClass


class ClientConfig(Config):
    """
    Configuration for the `Client`.

    Attributes
    ----------
    app_token : str
        The token for the twitch development app
    app_secret : str
        The secret for the twitch development app
    redirect_uri : str
        The redirect URI the internal server should reference for any awaiting user access tokens.
    log_level : str
        The logging level to use.
    """

    app_token = ''
    app_secret = ''
    redirect_uri = "http://localhost:8080/auth/callback"

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
    packets : `Emitter`
        An emitter which emits EventSub packets.
    api : `APIClient`
        The API client.
    es : `EventSubClient`
        The EventSub client.
    """

    def __init__(self, config):
        super(Client, self).__init__()
        self.config = config

        self.events = Emitter()

        # TODO: IRC CLIENT
        # TODO: API CLIENT
        # self.irc = IRCClient(self.config)
        # self.api = APIClient(self.config)
        self.es = EventSubClient(self)

        # TODO: Make methods to dynamically start a flask server or not :)
        self.running = gevent.event.Event()


    def shutdown(self):
        self.log.info("Graceful shutdown initiated")

        # TODO: Make shutdown methods for each mod
        self.es.shutdown()
        self.running.set()



    def start(self):
        """
        Main Client "Eventloop" a blocking request to keep the process running
        """
        # TODO: Start things here maybe
        self.es.run()

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
