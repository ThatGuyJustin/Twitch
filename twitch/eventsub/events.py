from six import with_metaclass

from twitch.types.base import ModelMeta, Field, Model, text, ListField, datetime, SlottedModel, enum
from twitch.types.channel import ChannelPointsReward, ChannelSubscription, \
    ChannelSubscriptionMessage, HypeTrain, ChannelGuestStarState, ChannelPoll, ChannelPointsRewardRedemptionStatus, \
    ChannelPrediction, ChannelPredictionStatus, ShieldMode, ShoutOut, Goal, StreamOnlineType, \
    ChannelGuestStarGroupLayout
from twitch.types.charity import Charity, CharityDonationAmount
from twitch.types.entitlement import DropEntitlementData
from twitch.types.extension import Product
from twitch.types.user import User
from twitch.util.string import get_event_name_from_doc_string

# Mapping of twitch event name to our event classes
EVENTS_MAP = {}


class EventSubEventMeta(ModelMeta):
    def __new__(mcs, name, parents, dct):
        obj = super(EventSubEventMeta, mcs).__new__(mcs, name, parents, dct)

        if name != 'EventSubEvent':
            EVENTS_MAP[get_event_name_from_doc_string(obj.__doc__)] = obj

        return obj


class EventSubEvent(with_metaclass(EventSubEventMeta, Model)):
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
class ChannelBan(EventSubEvent):
    """
    Twitch Name: 'channel.ban'
    """
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
class ChannelSubscribe(EventSubEvent):
    """
    Twitch Name: 'channel.subscribe'
    """
    _tier = Field(text, alias='tier')
    is_gift = Field(bool)

    @property
    def tier(self):
        return int(self._tier.replace('0', '', -1))


@wraps_model(BaseEvent)
class ChannelCheer(EventSubEvent):
    """
    Twitch Name: 'channel.cheer'
    """
    is_anonymous = Field(bool)
    message = Field(text)
    bits = Field(int)


class ChannelUpdate(EventSubEvent):
    """
    Twitch Name: 'channel.update'
    """
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
class ChannelUnban(EventSubEvent):
    """
    Twitch Name: 'channel.unban'
    """
    moderator_user_id = Field(int)
    moderator_user_login = Field(text)
    moderator_user_name = Field(text)

    @property
    def moderator(self):
        return User.create(data={"id": self.moderator_user_id, "login": self.moderator_user_login,
                                "name": self.moderator_user_name})


@wraps_model(BaseEvent)
class ChannelFollow(EventSubEvent):
    """
    Twitch Name: 'channel.follow'
    """
    followed_at = Field(datetime)


class ChannelRaid(EventSubEvent):
    """
    Twitch Name: 'channel.raid'
    """
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
class ChannelModeratorAdd(EventSubEvent):
    """
    Twitch Name: 'channel.moderator.add'
    """
    pass


@wraps_model(BaseEvent)
class ChannelModeratorRemove(EventSubEvent):
    """
    Twitch Name: 'channel.moderator.remove'
    """
    pass


@wraps_model(Broadcaster)
class ChannelGuestStarSessionBegin(EventSubEvent):
    """
    Twitch Name: 'channel.guest_star_session.begin'
    """
    session_id = Field(text)
    started_at = Field(datetime)


@wraps_model(Broadcaster)
class ChannelGuestStarSessionEnd(EventSubEvent):
    """
    Twitch Name: 'channel.guest_star_session.end'
    """
    session_id = Field(text)
    started_at = Field(datetime)
    ended_at = Field(datetime)


@wraps_model(Broadcaster)
class ChannelGuestStarGuestUpdate(EventSubEvent):
    """
    Twitch Name: 'channel.guest_star_session.update'
    """
    session_id = Field(text)
    moderator_user_id = Field(int, create=False)
    moderator_user_name = Field(text, create=False)
    moderator_user_login = Field(text, create=False)
    guest_user_id = Field(int)
    guest_user_name = Field(text)
    guest_user_login = Field(text)
    slot_id = Field(int)
    state = Field(enum(ChannelGuestStarState))
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
class ChannelGuestStarSettingsUpdate(EventSubEvent):
    """
    Twitch Name: 'channel.guest_star_settings.update'
    """
    is_moderator_send_live_enabled = Field(bool)
    slot_count = Field(int)
    is_browser_source_audio_enabled = Field(bool)
    group_layout = Field(enum(ChannelGuestStarGroupLayout))


@wraps_model(ChannelPoll)
class ChannelPollBegin(EventSubEvent):
    """
    Twitch Name: 'channel.poll.begin'
    """


@wraps_model(ChannelPoll)
class ChannelPollUpdate(EventSubEvent):
    """
    Twitch Name: 'channel.poll.progress'
    """


@wraps_model(ChannelPoll)
class ChannelPollEnd(EventSubEvent):
    """
    Twitch Name: 'channel.poll.end'
    """


@wraps_model(ChannelPointsReward)
class ChannelPointsCustomRewardAdd(EventSubEvent):
    """
    Twitch Name: 'channel.channel_points_custom_reward.add'
    """


@wraps_model(ChannelPointsReward)
class ChannelPointsCustomRewardUpdate(EventSubEvent):
    """
    Twitch Name: 'channel.channel_points_custom_reward.update'
    """


@wraps_model(ChannelPointsReward)
class ChannelPointsCustomRewardRemove(EventSubEvent):
    """
    Twitch Name: 'channel.channel_points_custom_reward.remove'
    """


@wraps_model(BaseEvent)
class ChannelPointsCustomRewardRedemptionAdd(EventSubEvent):
    """
    Twitch Name: 'channel.channel_points_custom_reward_redemption.add'
    """
    id = Field(text)
    user_input = Field(text)
    status = Field(enum(ChannelPointsRewardRedemptionStatus), default=ChannelPointsRewardRedemptionStatus.UNFULFILLED)
    reward = Field(ChannelPointsReward)
    redeemed_at = Field(datetime)


@wraps_model(BaseEvent)
class ChannelPointsCustomRewardRedemptionUpdate(EventSubEvent):
    """
    Twitch Name: 'channel.channel_points_custom_reward_redemption.update'
    """
    id = Field(text)
    user_input = Field(text)
    status = Field(enum(ChannelPointsRewardRedemptionStatus))
    reward = Field(ChannelPointsReward)
    redeemed_at = Field(datetime)


@wraps_model(ChannelPrediction)
class ChannelPredictionBegin(EventSubEvent):
    """
    Twitch Name: 'channel.prediction.begin'
    """
    pass


@wraps_model(ChannelPrediction)
class ChannelPredictionProgress(EventSubEvent):
    """
    Twitch Name: 'channel.prediction.progress'
    """
    pass


@wraps_model(ChannelPrediction)
class ChannelPredictionLock(EventSubEvent):
    """
    Twitch Name: 'channel.prediction.lock'
    """
    pass


@wraps_model(ChannelPrediction)
class ChannelPredictionEnd(EventSubEvent):
    """
    Twitch Name: 'channel.prediction.end'
    """
    winning_outcome_id = Field(text)
    status = Field(enum(ChannelPredictionStatus))


@wraps_model(ChannelSubscription)
class ChannelSubscriptionEnd(EventSubEvent):
    """
    Twitch Name: 'channel.subscription.end'
    """
    pass


@wraps_model(ChannelSubscription)
class ChannelSubscriptionGift(EventSubEvent):
    """
    Twitch Name: 'channel.subscription.gift'
    """
    total = Field(int)
    cumulative_total = Field(int, default=None)
    is_anonymous = Field(bool)


@wraps_model(ChannelSubscription)
class ChannelSubscriptionMessage(EventSubEvent):
    """
    Twitch Name: 'channel.subscription.message'
    """
    message = Field(ChannelSubscriptionMessage)
    cumulative_months = Field(int)
    streak_months = Field(int)
    duration_months = Field(int)


@wraps_model(Charity)
class CharityDonation(EventSubEvent):
    """
    Twitch Name: 'channel.charity_campaign.donate'
    """
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)
    amount = Field(CharityDonationAmount)

    @property
    def user(self):
        return User.create(data={"id": self.user_id, "login": self.user_login, "name": self.user_name})


@wraps_model(Charity)
class CharityCampaignStart(EventSubEvent):
    """
    Twitch Name: 'channel.charity_campaign.start'
    """
    current_amount = Field(CharityDonationAmount)
    target_amount = Field(CharityDonationAmount)
    started_at = Field(datetime)


@wraps_model(Charity)
class CharityCampaignProgress(EventSubEvent):
    """
    Twitch Name: 'channel.charity_campaign.progress'
    """
    current_amount = Field(CharityDonationAmount)
    target_amount = Field(CharityDonationAmount)


@wraps_model(Charity)
class CharityCampaignStop(EventSubEvent):
    """
    Twitch Name: 'channel.charity_campaign.stop'
    """
    current_amount = Field(CharityDonationAmount)
    target_amount = Field(CharityDonationAmount)
    stopped_at = Field(datetime)


class DropEntitlementGrant(EventSubEvent):
    """
    Twitch Name: 'drop.entitlement.grant'
    """
    id = Field(text)
    data = ListField(DropEntitlementData, default=[])


@wraps_model(BaseEvent)
class ExtensionBitsTransactionCreate(EventSubEvent):
    """
    Twitch Name: 'extension.bits_transaction.create'
    """
    extension_client_id = Field(text)
    id = Field(text)
    product = Field(Product)


@wraps_model(Goal)
class GoalBegin(EventSubEvent):
    """
    Twitch Name: 'channel.goal.begin'
    """
    pass


@wraps_model(Goal)
class GoalProgress(EventSubEvent):
    """
    Twitch Name: 'channel.goal.progress'
    """
    pass


@wraps_model(Goal)
class GoalEnd(EventSubEvent):
    """
    Twitch Name: 'channel.goal.end'
    """
    pass


@wraps_model(HypeTrain)
class HypeTrainBegin(EventSubEvent):
    """
    Twitch Name: 'channel.hype_train.begin'
    """
    pass


@wraps_model(HypeTrain)
class HypeTrainProgress(EventSubEvent):
    """
    Twitch Name: 'channel.hype_train.progress'
    """
    pass


@wraps_model(HypeTrain)
class HypeTrainEnds(EventSubEvent):
    """
    Twitch Name: 'channel.hype_train.end'
    """
    pass


class StreamOnline(EventSubEvent):
    """
    Twitch Name: 'stream.online'
    """
    broadcaster_user_id = Field(text)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    type = Field(enum(StreamOnlineType))
    started_at = Field(datetime)

    @property
    def broadcaster(self):
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                 "name": self.broadcaster_user_name})


class StreamOffline(EventSubEvent):
    """
    Twitch Name: 'stream.offline'
    """
    broadcaster_user_id = Field(text)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)

    @property
    def broadcaster(self):
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                 "name": self.broadcaster_user_name})


class UserAuthorizationGrant(EventSubEvent):
    """
    Twitch Name: 'user.authorization.grant'
    """
    client_id = Field(text)
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)


class UserAuthorizationRevoke(EventSubEvent):
    """
    Twitch Name: 'user.authorization.revoke'
    """
    client_id = Field(text)
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)


class UserUpdate(EventSubEvent):
    """
    Twitch Name: 'user.update'
    """
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)
    email = Field(text)
    email_verified = Field(text)
    description = Field(text)


@wraps_model(ShieldMode)
class ShieldModeBegin(EventSubEvent):
    """
    Twitch Name: 'channel.shield_mode.begin'
    """
    pass


@wraps_model(ShieldMode)
class ShieldModeEnd(EventSubEvent):
    """
    Twitch Name: 'channel.shield_mode.end'
    """
    pass


@wraps_model(ShoutOut)
class ShoutOutCreate(EventSubEvent):
    """
    Twitch Name: 'channel.shoutout.create'
    """
    pass


@wraps_model(ShoutOut)
class ShoutOutReceived(EventSubEvent):
    """
    Twitch Name: 'channel.shoutout.receive'
    """
    pass
