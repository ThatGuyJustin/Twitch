from gevent import monkey  # noqa

monkey.patch_all()  # noqa

import argparse
import os
import logging
import platform
import signal

from twitch.util.logging import setup_logging
from twitch.client import Client, ClientConfig
from twitch.bot import Bot, BotConfig
from twitch.eventsub.client import EventSubClient, EventSubConfig
from twitch.irc.client import IRCConfig, IRCClient
from twitch.flask.server import FlaskServer, FlaskConfig

parser = argparse.ArgumentParser()

parser.add_argument('--run-flask', help='Run flask on this twitch client', action='store_true', default=False)
parser.add_argument('--run-irc', help='Run the irc client on this  twitch client', action='store_true', default=False)
parser.add_argument('--run-eventsub', help='Run the eventsub client on this twitch client', action='store_true',default=False)
parser.add_argument('--run-bot', help='Run a Twitch bot on this twitch client', action='store_true', default=False)
parser.add_argument('--plugin', help='Load plugins into the bot', nargs='*', default=[])
parser.add_argument('--config', help='Configuration file', default=None)
parser.add_argument('--use-sigint', help='Use twitch.cli\'s built in signal handler for catching shutdown requests',action='store_true', default=True)


class CLI:
    def __init__(self):
        self.args = parser.parse_args()

        self._config = None
        self._client = None
        self._bot = None

        if self.args.config:
            self._config = ClientConfig.from_file(self.args.config)
        else:
            if os.path.exists('config.json'):
                self._config = ClientConfig.from_file('config.json')
            elif os.path.exists('config.yaml'):
                self._config = ClientConfig.from_file('config.yaml')
            else:
                self._config = ClientConfig()

        # TODO: config override from args

        if self.args.use_sigint:
            signal.signal(signal.SIGINT, self.hook_shutdown)
            signal.signal(signal.SIGTERM, self.hook_shutdown)

            if platform.system() != "Windows":
                signal.signal(signal.SIGUSR1, self.hook_shutdown)

        setup_logging(level=getattr(logging, self._config.log_level.upper()))

        self._client = Client(self._config)
        self._client.cli = self

        if self.args.run_flask or hasattr(self._config, 'flask'):
            self._client.flask = FlaskServer(self._client, FlaskConfig(self._config.flask) if hasattr(self._config, 'flask') else FlaskConfig())

        if self.args.run_eventsub or hasattr(self._config, 'eventsub'):
            self._client.es = EventSubClient(self._client, EventSubConfig(self._config.eventsub) if hasattr(self._config, 'eventsub') else EventSubConfig())

        if self.args.run_irc or hasattr(self._config, 'irc'):
            self._client.irc = IRCClient(self._client, IRCConfig(self._config.irc) if hasattr(self._config, 'irc') else IRCConfig())


        if self.args.run_bot or hasattr(self._config, 'bot'):
            bot_config = BotConfig(self._config.bot) if hasattr(self._config, 'bot') else BotConfig()
            if not hasattr(bot_config, 'plugins'):
                bot_config.plugins = self.args.plugin
            else:
                bot_config.plugins += self.args.plugin

            self._bot = Bot(self._client, bot_config)

    def hook_shutdown(self, signum=None, frame=None):
        # TODO:maybe have some safeguards if .shutdown() isn't working
        self._client.shutdown()

    def get(self):
        return self._bot or self._client

    @staticmethod
    def run(cls=None):
        if not cls:
            cls = CLI()
        (cls._bot or cls._client).run_forever()


if __name__ == '__main__':
    CLI.run()
