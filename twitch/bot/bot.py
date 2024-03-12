from twitch.bot.command import CommandLevels, CommandEvent
from twitch.bot.plugin import find_loadable_plugins
from twitch.bot.storage import Storage
from twitch.util.config import Config
from twitch.util.enum import get_enum_value_by_name
from twitch.util.logging import LoggingClass
from twitch.util.serializer import Serializer
from twitch.util.threadlocal import ThreadLocal

try:
    import regex as re
except ImportError:
    import re
import os
import inspect
import importlib


class BotConfig(Config):
    """
    An object which is used to configure and define the runtime configuration for
    a bot.

    Attributes
    ----------
    levels : dict(int, str)
        Mapping of user IDs to :class:`twitch.bot.commands.CommandLevels`
        which is used for the default commands_level_getter.
    plugins : list[string]
        List of plugin modules to load.
    commands_enabled : bool
        Whether this bot instance should utilize command parsing. Generally this
        should be true, unless your bot is only handling events and has no user
        interaction.
    commands_require_mention : bool
        Whether messages must mention the bot to be considered for command parsing.
    commands_prefix : str
        A string prefix that is required for a message to be considered for
        command parsing.  **DEPRECATED**
    command_prefixes : list[string]
        A list of string prefixes that are required for a message to be considered
        for command parsing.
    commands_prefix_getter : Optional[function]
        A function which takes in a message object and returns an array of strings
        (prefixes).
    commands_level_getter : function
        If set, a function which when given a GuildMember or User, returns the
        relevant :class:`disco.bot.commands.CommandLevels`.
    commands_group_abbrev : bool
        If true, command groups may be abbreviated to the least common variation.
        E.g. the grouping 'test' may be abbreviated down to 't', unless 'tag' exists,
        in which case it may be abbreviated down to 'te'.
    plugin_config_provider : Optional[function]
        If set, this function will replace the default configuration loading
        function, which normally attempts to load a file located at config/plugin_name.fmt
        where fmt is the plugin_config_format. The function here should return
        a valid configuration object which the plugin understands.
    plugin_config_format : str
        The serialization format plugin configuration files are in.
    plugin_config_dir : str
        The directory plugin configuration is located within.
    """
    deprecated = {'commands_prefix': 'command_prefixes'}

    levels = {}
    plugins = []
    plugin_config = {}
    shared_config = {}

    commands_enabled = True
    commands_require_mention = True
    commands_prefix = ''  # now deprecated
    command_prefixes = []
    commands_prefix_getter = None
    commands_level_getter = None
    commands_group_abbrev = True

    plugin_config_provider = None
    plugin_config_format = 'json'
    plugin_config_dir = 'config'

    storage_enabled = False
    storage_fsync = True
    storage_serializer = 'json'
    storage_path = 'storage.json'


class Bot(LoggingClass):
    user = None

    def __init__(self, client, config=None):
        self.client = client
        self.config = config or BotConfig()

        # The context carries information about events in a threadlocal storage
        self.ctx = ThreadLocal()

        # The storage object acts as a dynamic contextual aware store
        self.storage = None
        if self.config.storage_enabled:
            self.storage = Storage(self.ctx, self.config.from_prefix('storage'))

        self.plugins = {}
        self.group_abbrev = {}

        # Only bind event listeners if we're going to parse commands
        if self.config.commands_enabled and (self.config.commands_require_mention or len(self.config.command_prefixes)):
            # TODO: Map with IRC Message get
            self.client.events.on('ChatMessageReceive', self.on_message_create)

        # If we have a level getter, and it is a string, try to load it
        if isinstance(self.config.commands_level_getter, str):
            mod, func = self.config.commands_level_getter.rsplit('.', 1)
            mod = importlib.import_module(mod)
            self.config.commands_level_getter = getattr(mod, func)

        # Stores the last message for every single channel
        self.last_message_cache = {}

        # Stores a giant regex matcher for all commands
        self.command_matches_re = None

        # Finally, load all the plugin modules that where passed with the config
        for plugin_mod in self.config.plugins:
            self.add_plugin_module(plugin_mod)

        # Convert our configured mapping of entities to levels into something
        #  we can actually use. This ensures IDs are converted properly, and maps
        #  any level names (e.g. `user_id: admin`) map to their numerical values.
        for entity_id, level in tuple(self.config.levels.items()):
            del self.config.levels[entity_id]
            entity_id = int(entity_id) if str(entity_id).isdigit() else entity_id
            level = int(level) if str(level).isdigit() else get_enum_value_by_name(CommandLevels, level)
            self.config.levels[entity_id] = level

        # Bind the auth IRC event to map the logged-in user for reference.
        self.client.events.on("ChatReady", self.on_irc_auth)

    @property
    def commands(self):
        """
        Generator of all commands the bots plugins have defined.
        """
        for plugin in self.plugins.values():
            for command in plugin.commands:
                yield command

    def recompute(self):
        """
        Called when a plugin is loaded/unloaded to recompute internal state.
        """
        if self.config.commands_group_abbrev:
            groups = {command.group for command in self.commands if command.group}
            self.group_abbrev = self.compute_group_abbrev(groups)

        self.compute_command_matches_re()

    def compute_group_abbrev(self, groups):
        """
        Computes all possible abbreviations for a command grouping.
        """
        # For the first pass, we just want to compute each groups possible
        #  abbreviations that don't conflict with each other.
        possible = {}
        for group in groups:
            for index in range(1, len(group)):
                current = group[:index]
                if current in possible:
                    possible[current] = None
                else:
                    possible[current] = group

        # Now, we want to compute the actual shortest abbreviation out of the
        #  possible ones
        result = {}
        for abbrev, group in possible.items():
            if not group:
                continue

            if group in result:
                if len(abbrev) < len(result[group]):
                    result[group] = abbrev
            else:
                result[group] = abbrev

        return result

    def compute_command_matches_re(self):
        """
        Computes a single regex which matches all possible command combinations.
        """
        commands = tuple(self.commands)
        re_str = '|'.join(command.regex(grouped=False) for command in commands)
        if re_str:
            self.command_matches_re = re.compile(re_str, re.I)
        else:
            self.command_matches_re = None

    # TODO: Update to fit twitch messages
    def get_commands_for_message(self, require_mention, mention_rules, prefixes, msg=None, content=None):
        """
        Generator of all commands that a given message object triggers, based on
        the bots plugins and configuration.

        Parameters
        ---------
        require_mention : bool
            Checks if the message starts with a mention (and then ignores the prefix(es))
        mention_rules : dict(str, bool)
            Whether `user`, `everyone`, and `role` mentions are allowed. Defaults to:
            `{'user': True, 'everyone': False, 'role': False}`
        prefixes : list[string]
            A list of prefixes to check the message starts with.
        msg : :class:`disco.types.message.Message`
            The message object to parse and find matching commands for.
        content : str
            The content a message would contain if we were providing a command from one.

        Yields
        -------
        tuple(:class:`disco.bot.command.Command`, `re.MatchObject`)
            All commands the message triggers.
        """
        if not (require_mention or len(prefixes)):
            return []

        content = msg.content if msg else content

        if require_mention and msg:
            mention_direct = f"@{self.user.display_name}" in content

            if mention_direct:
                content = content.replace(f"@{self.user.display_name}", '', 1)
            else:
                return []

            content = content.lstrip()

        if len(prefixes):
            # Scan through the prefixes to find the first one that matches.
            # This may lead to unexpected results, but said unexpectedness
            # should be easy to avoid. An example of the unexpected results
            # that may occur would be if one prefix was `!` and one was `!a`.
            proceed = False
            for prefix in prefixes:
                if prefix and content.startswith(prefix):
                    content = content[len(prefix):]
                    proceed = True
                    break

            if not proceed:
                return []

        try:
            if not self.command_matches_re or not self.command_matches_re.match(content, concurrent=True):
                return []
        except:
            if not self.command_matches_re or not self.command_matches_re.match(content):
                return []

        options = []
        for command in self.commands:
            try:
                match = command.compiled_regex.match(content, concurrent=True)
            except:
                match = command.compiled_regex.match(content)
            if match:
                options.append((command, match))

        return sorted(options, key=lambda obj: obj[0].group is None)

    def get_level(self, actor):
        level = CommandLevels.DEFAULT

        if callable(self.config.commands_level_getter):
            level = self.config.commands_level_getter(self, actor)
        else:
            if actor.id in self.config.levels:
                level = self.config.levels[actor.id]
            else:
                # TODO: Add emoji artist, and maybe move this over to a "default level getter" method instead?
                #   So this way levels aren't forced by default?
                for _type in ["broadcaster", "mod", "vip", "subscriber"]:
                    if getattr(actor, _type):
                        level = getattr(CommandLevels, _type.upper())
                        break

        return level

    def check_command_permissions(self, command, event):
        if not command.level:
            return True

        level = self.get_level(event.user)

        if level >= command.level:
            return True
        return False

    # TODO: Update TO TWITCH
    def handle_command_event(self, event, content=None):
        """
        Attempts to handle a newly created command events in the context of
        command parsing/triggering. Calls all relevant commands the message triggers.

        Parameters
        ---------
        event : :class:'Event'
            The newly created event object to parse/handle.
        content : :class:'Message'
            Used for on_message_update below

        Returns
        -------
        bool
            Whether any commands where successfully triggered by the message.
        """
        if self.config.commands_enabled:
            commands = []
            custom_message_prefixes = None
            if event.content:
                if self.config.commands_prefix_getter:
                    custom_message_prefixes = (self.config.commands_prefix_getter(event.content))

                commands = self.get_commands_for_message(
                    self.config.commands_require_mention,
                    {},
                    custom_message_prefixes or self.config.command_prefixes,
                    event,
                )

            elif content:
                commands = self.get_commands_for_message(False, {}, self.config.command_prefixes, content=event.content)

            if not len(commands):
                return False

            for command, match in commands:
                if not self.check_command_permissions(command, event):
                    continue

                if command.plugin.execute(CommandEvent(command, event, match, self.client)):
                    return True
            return False
        return

    def on_irc_auth(self, event):
        self.user = event

    def on_message_create(self, event):
        if event.user.id == self.user.user_id:
            return

        result = self.handle_command_event(event)

        self.last_message_cache[event.broadcaster_id] = (event, result)

    def add_plugin(self, inst, config=None, ctx=None):
        """
        Adds and loads a plugin, based on its class.

        Parameters
        ----------
        inst : subclass (or instance therein) of `disco.bot.plugin.Plugin`
            Plugin class to initialize and load.
        config : Optional
            The configuration to load the plugin with.
        ctx : Optional[dict]
            Context (previous state) to pass the plugin. Usually used along w/
            unload.
        """
        if inspect.isclass(inst):
            if not config:
                if callable(self.config.plugin_config_provider):
                    config = self.config.plugin_config_provider(inst)
                else:
                    config = self.load_plugin_config(inst)

            inst = inst(self, config)

        if inst.__class__.__name__ in self.plugins:
            self.log.warning('Attempted to add already added plugin %s', inst.__class__.__name__)
            raise Exception('Cannot add already added plugin: {}'.format(inst.__class__.__name__))

        self.ctx['plugin'] = self.plugins[inst.__class__.__name__] = inst
        self.plugins[inst.__class__.__name__].load(ctx or {})
        self.recompute()
        self.ctx.drop()

    def rmv_plugin(self, cls):
        """
        Unloads and removes a plugin based on its class.

        Parameters
        ----------
        cls : subclass of :class:`disco.bot.plugin.Plugin`
            Plugin class to unload and remove.
        """
        if not hasattr(cls, '__name__') or cls.__name__ not in self.plugins:
            try:
                cls = cls.__class__
                assert cls.__name__ in self.plugins
            except:
                raise Exception('Cannot remove non-existent plugin: {}'.format(cls.__name__))

        ctx = {}
        self.plugins[cls.__name__].unload(ctx)
        del self.plugins[cls.__name__]
        self.recompute()
        return ctx

    def reload_plugin(self, cls):
        """
        Reloads a plugin.
        """
        if not hasattr(cls, '__name__') or cls.__name__ not in self.plugins:
            try:
                cls = cls.__class__
                assert cls.__name__ in self.plugins
            except:
                raise Exception('Cannot reload non-existent plugin: {}'.format(cls.__name__))

        config = self.plugins[cls.__name__].config

        ctx = self.rmv_plugin(cls)
        module = importlib.reload(inspect.getmodule(cls))
        self.add_plugin(getattr(module, cls.__name__), config, ctx)

    def run_forever(self):
        """
        Runs this bots core loop forever.
        """
        self.client.run_forever()

    def add_plugin_module(self, path, config=None):
        """
        Adds and loads a plugin, based on its module path.
        """
        self.log.info(f'Adding plugin module at path "{path}"')
        mod = importlib.import_module(path)
        loaded = False

        plugins = find_loadable_plugins(mod)
        for plugin in plugins:
            loaded = True
            self.add_plugin(plugin, config)

        if not loaded:
            raise Exception(f'Could not find any plugins to load within module {path}')

    def load_plugin_config(self, cls):
        name = cls.__name__.lower()
        if name.endswith('plugin'):
            name = name[:-6]

        path = os.path.join(
            self.config.plugin_config_dir, name) + '.' + self.config.plugin_config_format

        data = {}
        if self.config.shared_config:
            data.update(self.config.shared_config)

        if name in self.config.plugin_config:
            data.update(self.config.plugin_config[name])

        if os.path.exists(path):
            with open(path, 'r') as f:
                data.update(Serializer.loads(self.config.plugin_config_format, f.read()))
                f.close()

        if hasattr(cls, 'config_cls'):
            inst = cls.config_cls()
            if data:
                inst.update(data)
            return inst

        return data
