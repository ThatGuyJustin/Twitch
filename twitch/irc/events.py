# Mapping of twitch event name to our event classes
from twitch.types.base import ModelMeta, Model, Field, SlottedModel, text, ListField, datetime
from twitch.types.chat import ChatMessage
from twitch.util.metaclass import with_metaclass

EVENTS_MAP = {}


class IRCChatEventMeta(ModelMeta):
    def __new__(mcs, name, parents, dct):
        obj = super(IRCChatEventMeta, mcs).__new__(mcs, name, parents, dct)

        if name != 'IRCChatEvent':
            EVENTS_MAP[name] = obj

        return obj


class IRCChatEvent(with_metaclass(IRCChatEventMeta, Model)):
    """
    The EventSubEvent class wraps various functionality for events passed to us
    over the pubsub websocket, and serves as a simple proxy to inner values for
    some wrapped event-types (e.g. MessageCreate only contains a message, so we
    proxy all attributes to the inner message object).
    """

    @staticmethod
    def from_dispatch(client, data):
        """
        Create a new GatewayEvent instance based on event data.
        """
        cls = EVENTS_MAP.get(data['event_name'])
        if not cls:
            raise Exception('Could not find cls for {} ({})'.format(data['event_name'], data))

        return cls.create(data['event'], client)

    @classmethod
    def create(cls, obj, client):
        """
        Create this GatewayEvent class from data and the client.
        """
        cls.raw_data = obj

        # If this event is wrapping a model, pull its fields
        if hasattr(cls, '_wraps_model'):
            alias, model = cls._wraps_model

            data = {
                k: obj.pop(k) for k in model._fields.keys() if k in obj
            }

            obj[alias] = data

        obj = cls(obj, client)

        if hasattr(cls, '_attach'):
            field, to = cls._attach
            setattr(getattr(obj, to[0]), to[1], getattr(obj, field))

        return obj

    def __getattr__(self, name):
        try:
            _proxy = object.__getattribute__(self, '_proxy')
        except AttributeError:
            return object.__getattribute__(self, name)

        try:
            return getattr(getattr(self, _proxy), name)
        except TypeError:
            return object.__getattribute__(self, name)


def debug(func=None, match=None):
    def deco(cls):
        old_init = cls.__init__

        def new_init(self, obj, *args, **kwargs):
            if not match or match(obj):
                if func:
                    print(func(obj))
                else:
                    print(obj)

            old_init(self, obj, *args, **kwargs)

        cls.__init__ = new_init
        return cls

    return deco


def wraps_model(model, alias=None):
    alias = alias or model.__name__.lower()

    def deco(cls):
        cls._fields[alias] = Field(model)
        cls._fields[alias].name = alias
        cls._wraps_model = (alias, model)
        cls._proxy = alias
        return cls

    return deco


def proxy(field):
    def deco(cls):
        cls._proxy = field
        return cls

    return deco


def attach(field, to=None):
    def deco(cls):
        cls._attach = (field, to)
        return cls

    return deco


class ChatReady(IRCChatEvent):
    user_id = Field(int)
    badge_info = Field(text)
    badges = Field(text)
    color = Field(text)
    display_name = Field(text)
    emote_sets = ListField(text)
    user_type = Field(text)


@wraps_model(ChatMessage)
class ChatMessageReceive(IRCChatEvent):
    pass


# TODO: Clean up timestamp
class ChatMessageDelete(IRCChatEvent):
    channel = Field(text)
    channel_id = Field(int)
    message = Field(text)
    message_id = Field(text)
    user = Field(text)
    tmi_timestamp = Field(text)


# TODO: Fix broken event
class ChatCleared(IRCChatEvent):
    channel = Field(text)
    channel_id = Field(int)
    user = Field(text, create=False)
    user_id = Field(int, create=False)
    ban_duration = Field(int, create=False)
    tmi_timestamp = Field(text, create=False)


class ChatNotice(IRCChatEvent):
    id = Field(text, create=False)
    channel = Field(text)
    message = Field(text)


# TODO: Map after testing
class ChatRoomUpdate(IRCChatEvent):
    emote_only = Field(bool, create=False)
    followers_only = Field(int, create=False)
    unique_only = Field(bool, create=False)
    channel = Field(text, create=False)
    channel_id = Field(int, create=False)
    slowmode = Field(int, create=False)
    sub_only = Field(bool, create=False)


# TODO: Additional Notice types, like raid and sub D:
class ChatUserNotice(IRCChatEvent):
    id = Field(text),
    msg_id = Field(text, create=False)
    system_msg = Field(text, create=False)
    tmi_timestamp = Field(text, create=False)
    channel = Field(text)
    channel_id = Field(int)
    message = Field(text)
    badge_info = Field(text, create=False)
    badges = Field(text, create=False)
    color = Field(text, create=False)
    emotes = Field(text, create=False)
    username = Field(text)
    user_id = Field(int)
    user_type = Field(text, default="normal")
    display_name = Field(text, create=False)
    mod = Field(bool, create=False)
    subscriber = Field(bool, create=False)
    turbo = Field(bool, create=False)


class ChatRoomPart(IRCChatEvent):
    channel = Field(text)
    user = Field(text)


class ChatRoomJoin(IRCChatEvent):
    channel = Field(text)
    user = Field(text)


# TODO: Map?
class ChatReconnect(IRCChatEvent):
    pass


class ChatWhisper(IRCChatEvent):
    id = Field(text)
    thread_id = Field(text)
    from_user = Field(text)
    to_user = Field(text)
    badges = Field(text, create=False)
    color = Field(text, create=False)
    display_name = Field(text, create=False)
    emotes = Field(text, create=False)
    user_id = Field(int, create=False)
    user_type = Field(text, create=False)


class ChatUserState(IRCChatEvent):
    pass
