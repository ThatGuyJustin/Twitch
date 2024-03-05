# Mapping of twitch event name to our event classes
from twitch.types.base import ModelMeta, Model, Field, SlottedModel, text, ListField
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


# TODO: Map after testing
class ChatRoomUpdate(IRCChatEvent):
    pass


class ChatRoomJoin(IRCChatEvent):
    pass


class ChatRoomLeave(IRCChatEvent):
    pass


# TODO: Map?
class ChatReconnect(IRCChatEvent):
    pass


class ChatWhisper(IRCChatEvent):
    pass


class ChatUserState(IRCChatEvent):
    pass
