from six import with_metaclass

from twitch.types.base import ModelMeta, Field, Model, text, ListField, datetime, SlottedModel
from twitch.types.channel import ChannelPointsReward, ChannelPredictionOutcomes, ChannelSubscription, \
    ChannelSubscriptionMessage, HypeTrain
from twitch.types.charity import Charity, CharityDonationAmount
from twitch.types.entitlement import DropEntitlementData
from twitch.types.extension import Product
from twitch.types.user import User
from twitch.util.string import underscore

# Mapping of twitch event name to our event classes
EVENTS_MAP = {}


class PubSubEventMeta(ModelMeta):
    def __new__(mcs, name, parents, dct):
        obj = super(PubSubEventMeta, mcs).__new__(mcs, name, parents, dct)

        # TODO: Make work with weird twitch event sub names
        # Such as "channel.guest_star_session.begin"
        # Notice how it has a "." delimiter, but also "_"'s between the words.
        if name != 'PubSubEvent':
            EVENTS_MAP[underscore(name)] = obj

        return obj


class PubSubEvent(with_metaclass(PubSubEventMeta, Model)):
    """
    The PubSubEvent class wraps various functionality for events passed to us
    over the pubsub websocket, and serves as a simple proxy to inner values for
    some wrapped event-types (e.g. MessageCreate only contains a message, so we
    proxy all attributes to the inner message object).
    """

    @staticmethod
    def from_dispatch(client, data):
        """
        Create a new GatewayEvent instance based on event data.
        """
        cls = EVENTS_MAP.get(data['metadata']['subscription_type'])
        if not cls:
            raise Exception('Could not find cls for {} ({})'.format(data['metadata']['subscription_type'], data))

        return cls.create(data['payload']['event'], client)

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


class BaseEvent(SlottedModel):
    user_id = Field(int)
    user_login = Field(text)
    user_name = Field(text)
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)

    @property
    def user(self):
        return User.create(data={"id": self.user_id, "login": self.user_login, "name": self.user_name})

    @property
    def broadcaster(self):
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                 "name": self.broadcaster_user_name})


class Broadcaster(SlottedModel):
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)

    @property
    def broadcaster(self):
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                 "name": self.broadcaster_user_name})


@wraps_model(BaseEvent)
class ChannelBan(PubSubEvent):
    moderator_user_id = Field(int)
    moderator_user_login = Field(text)
    moderator_user_name = Field(text)
    reason = Field(text)
    banned_at = Field(datetime)
    ends_at = Field(datetime)
    is_permanent = Field(bool)

    @property
    def moderator(self):
        return User.create(data={"id": self.moderator_user_id, "login": self.moderator_user_login,
                                "name": self.moderator_user_name})


@wraps_model(BaseEvent)
class ChannelSubscribe(PubSubEvent):
    _tier = Field(text, alias='tier')
    is_gift = Field(bool)

    @property
    def tier(self):
        return int(self._tier.replace('0', '', -1))


@wraps_model(BaseEvent)
class ChannelCheer(PubSubEvent):
    is_anonymous = Field(bool)
    message = Field(text)
    bits = Field(int)


class ChannelUpdate(PubSubEvent):
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    title = Field(text)
    language = Field(text)
    category_id = Field(int)
    category_name = Field(text)
    content_classification_labels = ListField(text, default=[])

    @property
    def broadcaster(self):
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                "name": self.broadcaster_user_name})


@wraps_model(BaseEvent)
class ChannelUnban(PubSubEvent):
    moderator_user_id = Field(int)
    moderator_user_login = Field(text)
    moderator_user_name = Field(text)

    @property
    def moderator(self):
        return User.create(data={"id": self.moderator_user_id, "login": self.moderator_user_login,
                                "name": self.moderator_user_name})


@wraps_model(BaseEvent)
class ChannelFollow(PubSubEvent):
    followed_at = Field(datetime)


class ChannelRaid(PubSubEvent):
    from_broadcaster_user_id = Field(int)
    from_broadcaster_user_login = Field(text)
    from_broadcaster_user_name = Field(text)
    to_broadcaster_user_id = Field(text)
    to_broadcaster_user_login = Field(text)
    to_broadcaster_user_name = Field(text)
    viewers = Field(int)

    @property
    def raider(self):
        return User.create(data={"id": self.from_broadcaster_user_id, "login": self.from_broadcaster_user_login,
                                 "name": self.from_broadcaster_user_name})

    @property
    def raided(self):
        return User.create(data={"id": self.to_broadcaster_user_id, "login": self.to_broadcaster_user_login,
                                 "name": self.to_broadcaster_user_name})


@wraps_model(BaseEvent)
class ChannelModeratorAdd(PubSubEvent):
    """

    """


@wraps_model(BaseEvent)
class ChannelModeratorRemove(PubSubEvent):
    """

    """


@wraps_model(Broadcaster)
class ChannelGuestStarSessionBegin(PubSubEvent):
    session_id = Field(text)
    started_at = Field(datetime)


@wraps_model(Broadcaster)
class ChannelGuestStarSessionEnd(PubSubEvent):
    session_id = Field(text)
    started_at = Field(datetime)
    ended_at = Field(datetime)


@wraps_model(Broadcaster)
class ChannelGuestStarGuestUpdate(PubSubEvent):
    session_id = Field(text)
    moderator_user_id = Field(int)
    moderator_user_name = Field(text)
    moderator_user_login = Field(text)
    guest_user_id = Field(int)
    guest_user_name = Field(text)
    guest_user_login = Field(text)
    slot_id = Field(int)
    # TODO: Enum this
    state = Field(text)
    host_video_enabled = Field(bool, default=None)
    host_audio_enabled = Field(bool, default=None)
    host_volume = Field(int, default=None)

    @property
    def moderator(self):
        return User.create(data={"id": self.moderator_user_id, "login": self.moderator_user_name,
                                 "name": self.moderator_user_login})

    @property
    def guest(self):
        return User.create(data={"id": self.guest_user_id, "login": self.guest_user_name,
                                 "name": self.guest_user_login})


@wraps_model(Broadcaster)
class ChannelGuestStarSettingsUpdate(PubSubEvent):
    is_moderator_send_live_enabled = Field(bool)
    slot_count = Field(int)
    is_browser_source_audio_enabled = Field(bool)
    # TODO: Enum this
    group_layout = Field(text)


@wraps_model(Broadcaster)
class ChannelPollEvent(PubSubEvent):
    id = Field(int)
    title = Field(text)
    # TODO: Make Poll Choices a type
    choices = ListField(text, default=[])
    # TODO: Make bits_voting a type
    bits_voting = Field(None)
    # TODO: Make channel_points_voting SETTINGS a type
    channel_points_voting = Field(None)
    started_at = Field(datetime)
    ends_at = Field(datetime)


@wraps_model(ChannelPollEvent)
class ChannelPollBegin(PubSubEvent):
    """

    """


@wraps_model(ChannelPollEvent)
class ChannelPollUpdate(PubSubEvent):
    """

    """


@wraps_model(ChannelPollEvent)
class ChannelPollEnd(PubSubEvent):
    # TODO: Make this an enum
    status = Field(text)


@wraps_model(ChannelPointsReward)
class ChannelPointsCustomRewardAdd(PubSubEvent):
    """

    """


@wraps_model(ChannelPointsReward)
class ChannelPointsCustomRewardUpdate(PubSubEvent):
    """

    """


@wraps_model(ChannelPointsReward)
class ChannelPointsCustomRewardRemove(PubSubEvent):
    """

    """


@wraps_model(BaseEvent)
class ChannelPointsCustomRewardRedemptionAdd(PubSubEvent):
    id = Field(text)
    user_input = Field(text)
    # TODO: Convert to Enum
    status = Field(text)
    reward = Field(ChannelPointsReward)
    redeemed_at = Field(datetime)


@wraps_model(BaseEvent)
class ChannelPointsCustomRewardRedemptionUpdate(PubSubEvent):
    id = Field(text)
    user_input = Field(text)
    # TODO: Convert to Enum
    status = Field(text)
    reward = Field(ChannelPointsReward)
    redeemed_at = Field(datetime)


@wraps_model(Broadcaster)
class ChannelPredictionBegin(PubSubEvent):
    id = Field(text)
    title = Field(text)
    outcomes = ListField(ChannelPredictionOutcomes)
    started_at = Field(datetime)
    locks_at = Field(datetime)


@wraps_model(Broadcaster)
class ChannelPredictionProgress(PubSubEvent):
    id = Field(text)
    title = Field(text)
    outcomes = ListField(ChannelPredictionOutcomes)
    started_at = Field(datetime)
    locks_at = Field(datetime)


@wraps_model(Broadcaster)
class ChannelPredictionLock(PubSubEvent):
    id = Field(text)
    title = Field(text)
    outcomes = ListField(ChannelPredictionOutcomes)
    started_at = Field(datetime)
    locks_at = Field(datetime)


@wraps_model(Broadcaster)
class ChannelPredictionLock(PubSubEvent):
    id = Field(text)
    title = Field(text)
    winning_outcome_id = Field(text)
    outcomes = ListField(ChannelPredictionOutcomes)
    # TODO: Convert to enum
    status = Field(text)
    started_at = Field(datetime)
    ended_at = Field(datetime)


@wraps_model(ChannelSubscription)
class ChannelSubscriptionEnd(PubSubEvent):
    """

    """


@wraps_model(ChannelSubscription)
class ChannelSubscriptionGift(PubSubEvent):
    total = Field(int)
    cumulative_total = Field(int, default=None)
    is_anonymous = Field(bool)


@wraps_model(ChannelSubscription)
class ChannelSubscriptionMessage(PubSubEvent):
    message = Field(ChannelSubscriptionMessage)
    cumulative_months = Field(int)
    streak_months = Field(int)
    duration_months = Field(int)


@wraps_model(Charity)
class CharityDonation(PubSubEvent):
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)
    amount = Field(CharityDonationAmount)

    @property
    def user(self):
        return User.create(data={"id": self.user_id, "login": self.user_login, "name": self.user_name})


@wraps_model(Charity)
class CharityCampaignStart(PubSubEvent):
    current_amount = Field(CharityDonationAmount)
    target_amount = Field(CharityDonationAmount)
    started_at = Field(datetime)


@wraps_model(Charity)
class CharityCampaignProgress(PubSubEvent):
    current_amount = Field(CharityDonationAmount)
    target_amount = Field(CharityDonationAmount)


@wraps_model(Charity)
class CharityCampaignStop(PubSubEvent):
    current_amount = Field(CharityDonationAmount)
    target_amount = Field(CharityDonationAmount)
    stopped_at = Field(datetime)


class DropEntitlementGrant(PubSubEvent):
    id = Field(text)
    data = ListField(DropEntitlementData, default=[])


@wraps_model(BaseEvent)
class ExtensionBitsTransactionCreate(PubSubEvent):
    extension_client_id = Field(text)
    id = Field(text)
    product = Field(Product)


@wraps_model(BaseEvent)
class Goals(PubSubEvent):
    id = Field(text)
    broadcaster_user_id = Field(text)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    # TODO: Turn into an enum
    type = Field(text)
    description = Field(text)
    is_achieved = Field(bool)
    current_amount = Field(int)
    target_amount = Field(int)
    started_at = Field(datetime)
    ended_at = Field(datetime, default=None)

    @property
    def broadcaster(self):
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                 "name": self.broadcaster_user_name})


@wraps_model(HypeTrain)
class HypeTrainBegin(PubSubEvent):
    """
    """
    pass


@wraps_model(HypeTrain)
class HypeTrainProgress(PubSubEvent):
    """
    """
    pass


@wraps_model(HypeTrain)
class HypeTrainEnds(PubSubEvent):
    """
    """
    pass


# TODO: Map the Channel shoutout events along with the shield mode events


class StreamOnline(PubSubEvent):
    broadcaster_user_id = Field(text)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    # TODO: ENUM THIS!
    type = Field(text)
    started_at = Field(datetime)

    @property
    def broadcaster(self):
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                 "name": self.broadcaster_user_name})


class StreamOffline(PubSubEvent):
    broadcaster_user_id = Field(text)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)

    @property
    def broadcaster(self):
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                 "name": self.broadcaster_user_name})


class UserAuthorizationGrant(PubSubEvent):
    client_id = Field(text)
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)


class UserAuthorizationRevoke(PubSubEvent):
    client_id = Field(text)
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)


class UserUpdate(PubSubEvent):
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)
    email = Field(text)
    email_verified = Field(text)
    description = Field(text)
