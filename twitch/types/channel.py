from twitch.types.base import SlottedModel, Field, text, datetime, ListField, enum
from twitch.types.user import User


class ChannelGuestStarGroupLayout:
    TILED = "tiled"
    SCREENSHARE = "screenshare"
    HORIZONTAL_TOP = "horizontal_top"
    HORIZONTAL_BOTTOM = "horizontal_bottom"
    VERTICAL_LEFT = "vertical_left"
    VERTICAL_RIGHT = "vertical_right"


class ChannelGuestStarState:
    INVITED = "invited"
    ACCEPTED = "accepted"
    READY = "ready"
    BACKSTAGE = "backstage"
    LIVE = "live"
    REMOVED = "removed"


class ChannelPollChoices(SlottedModel):
    id = Field(text)
    title = Field(text)
    bits_votes = Field(text)
    channel_points_votes = Field(text)
    votes = Field(int)


class ChannelPollVoteSettings(SlottedModel):
    is_enabled = Field(bool)
    amount_per_vote = Field(int)


class ChannelPollStatus:
    COMPLETED = "completed"
    ARCHIVED = "archived"
    TERMINATED = "terminated"


class ChannelPoll(SlottedModel):
    id = Field(text)
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    title = Field(text)
    choices = ListField(ChannelPollChoices, default=[])
    bits_voting = Field(ChannelPollVoteSettings)
    channel_points_voting = Field(ChannelPollVoteSettings)
    started_at = Field(datetime)
    ends_at = Field(datetime)
    status = Field(enum(ChannelPollStatus), create=False)

    @property
    def broadcaster(self):
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                 "name": self.broadcaster_user_name})


class ChannelPointsRewardRedemptionStatus:
    UNFULFILLED = "unfulfilled"
    UNKNOWN = "unknown"
    FULFILLED = "fulfilled"
    CANCELED = "canceled"


class ChannelPointsRewardImage(SlottedModel):
    url_1x = Field(text)
    url_2x = Field(text)
    url_4x = Field(text)


class ChannelPointsRewardMaxPerStream(SlottedModel):
    is_enabled = Field(bool)
    value = Field(int)


class ChannelPointsRewardGlobalCooldown(SlottedModel):
    is_enabled = Field(bool)
    seconds = Field(int)


class ChannelPointsReward(SlottedModel):
    id = Field(text)
    broadcaster_user_id = Field(int, create=False)
    broadcaster_user_login = Field(text, create=False)
    broadcaster_user_name = Field(text, create=False)
    is_enabled = Field(bool, create=False)
    is_paused = Field(bool, create=False)
    is_in_stock = Field(bool, create=False)
    title = Field(text)
    cost = Field(int)
    prompt = Field(text)
    is_user_input_required = Field(bool, create=False)
    should_redemptions_skip_request_queue = Field(bool, create=False)
    max_per_stream = Field(ChannelPointsRewardMaxPerStream, create=False)
    max_per_user_per_stream = Field(ChannelPointsRewardMaxPerStream, create=False)
    background_color = Field(text, create=False)
    image = Field(ChannelPointsRewardImage, create=False)
    default_image = Field(ChannelPointsRewardImage, create=False)
    global_cooldown = Field(ChannelPointsRewardGlobalCooldown, create=False)
    cooldown_expires_at = Field(datetime, default=None, create=False)
    redemptions_redeemed_current_stream = Field(int, default=None, create=False)

    @property
    def broadcaster(self):
        return User(id=self.broadcaster_user_id, login=self.broadcaster_user_login,
                    name=self.broadcaster_user_name) if self.broadcaster_user_id else None


class ChannelPredictionTopPredictors(SlottedModel):
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)
    channel_points_won = Field(int)
    channel_points_used = Field(int)

    @property
    def user(self):
        return User(id=self.user_id, login=self.user_login, name=self.user_name)


class ChannelPredictionOutcomes(SlottedModel):
    id = Field(text)
    title = Field(text)
    color = Field(text)
    users = Field(int)
    channel_points = Field(int)
    top_predictors = ListField(ChannelPredictionTopPredictors, default=[])


class ChannelPredictionStatus:
    RESOLVED = "resolved"
    CANCELED = "canceled"


class ChannelPrediction(SlottedModel):
    id = Field(text)
    title = Field(text)
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    outcomes = ListField(ChannelPredictionOutcomes)
    started_at = Field(datetime)
    locks_at = Field(datetime, create=False)
    ended_at = Field(datetime, create=False)

    @property
    def broadcaster(self):
        return User(id=self.broadcaster_user_id, login=self.broadcaster_user_login,
                    name=self.broadcaster_user_name)


class ChannelSubscriptionMessageEmotes(SlottedModel):
    begin = Field(int)
    end = Field(int)
    id = Field(text)


class ChannelSubscriptionMessage(SlottedModel):
    text = Field(text)
    emotes = ListField(ChannelSubscriptionMessageEmotes)


class ChannelSubscription(SlottedModel):
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    tier = Field(int)
    message = Field(ChannelSubscriptionMessage, create=False)

    # @property
    # def tier(self):
    #     return int(self._tier.replace('0', '', -1))


class GoalType:
    FOLLOW = "follower"
    SUBSCRIPTION = "subscription"
    SUBSCRIPTION_COUNT = "subscription_count"
    NEW_SUBSCRIPTION = "new_subscription"
    NEW_SUBSCRIPTION_COUNT = "new_subscription_count"


class Goal(SlottedModel):
    id = Field(text)
    broadcaster_user_id = Field(text)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    type = Field(enum(GoalType))
    description = Field(text)
    is_achieved = Field(bool)
    current_amount = Field(int)
    target_amount = Field(int)
    started_at = Field(datetime)
    ended_at = Field(datetime, default=None)

    @property
    def broadcaster(self):
        return User(id=self.broadcaster_user_id, login=self.broadcaster_user_login,
                    name=self.broadcaster_user_name)


class HypeTrainContributionType:
    BITS = "bits"
    SUBSCRIPTION = "subscription"
    OTHER = "OTHER"


class HypeTrainContribution(SlottedModel):
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)
    type = Field(enum(HypeTrainContributionType))
    total = Field(int)

    @property
    def user(self):
        return User(id=self.user_id, login=self.user_login, name=self.user_name)


class HypeTrain(SlottedModel):
    id = Field(text)
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    total = Field(int)
    progress = Field(int)
    goal = Field(int)
    top_contributions = ListField(HypeTrainContribution)
    last_contribution = Field(HypeTrainContribution)
    level = Field(text)
    started_at = Field(datetime)
    expires_at = Field(datetime, create=False)
    ended_at = Field(datetime, create=False)
    cooldown_ends_at = Field(datetime, create=False)

    @property
    def broadcaster(self):
        return User(id=self.broadcaster_user_id, login=self.broadcaster_user_login,
                    name=self.broadcaster_user_name)


class ShieldMode(SlottedModel):
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    moderator_user_id = Field(int)
    moderator_user_login = Field(text)
    moderator_user_name = Field(text)
    started_at = Field(datetime, create=False)
    ended_at = Field(datetime, create=False)

    @property
    def broadcaster(self):
        return User(id=self.broadcaster_user_id, login=self.broadcaster_user_login,
                    name=self.broadcaster_user_name)

    @property
    def moderator(self):
        return User(id=self.moderator_user_id, login=self.moderator_user_login, name=self.moderator_user_name)


class ShoutOut(SlottedModel):
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    to_broadcaster_user_id = Field(int, create=False)
    to_broadcaster_user_login = Field(text, create=False)
    to_broadcaster_user_name = Field(text, create=False)
    from_broadcaster_user_id = Field(int, create=False)
    from_broadcaster_user_login = Field(text, create=False)
    from_broadcaster_user_name = Field(text, create=False)
    moderator_user_id = Field(int, create=False)
    moderator_user_login = Field(text, create=False)
    moderator_user_name = Field(text, create=False)
    viewer_count = Field(int)
    started_at = Field(datetime)
    cooldown_ends_at = Field(datetime)
    target_cooldown_ends_at = Field(datetime)

    @property
    def broadcaster(self):
        return User(id=self.broadcaster_user_id, login=self.broadcaster_user_login,
                    name=self.broadcaster_user_name)

    @property
    def to_broadcaster(self):
        return User(id=self.to_broadcaster_user_id, login=self.to_broadcaster_user_login,
                    name=self.to_broadcaster_user_name)

    @property
    def from_broadcaster(self):
        return User(id=self.from_broadcaster_user_id, login=self.from_broadcaster_user_login,
                    name=self.from_broadcaster_user_name)

    @property
    def moderator(self):
        return User(id=self.moderator_user_id, login=self.moderator_user_login, name=self.moderator_user_name)


class StreamOnlineType:
    LIVE = "live"
    PLAYLIST = "playlist"
    WATCH_PARTY = "watch_party"
    PREMIERE = "premiere"
    RE_RUN = "re_run"
