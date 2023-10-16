from twitch.types.base import SlottedModel, Field, text, datetime, ListField
from twitch.types.user import User


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
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                 "name": self.broadcaster_user_name}) if self.broadcaster_user_id else None


class ChannelPredictionTopPredictors(SlottedModel):
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)
    channel_points_won = Field(int)
    channel_points_used = Field(int)

    @property
    def user(self):
        return User.create(data={"id": self.user_id, "login": self.user_login,
                                 "name": self.user_name})


class ChannelPredictionOutcomes(SlottedModel):
    id = Field(text)
    title = Field(text)
    color = Field(text)
    users = Field(int)
    channel_points = Field(int)
    top_predictors = ListField(ChannelPredictionTopPredictors, default=[])


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
    _tier = Field(text, alias='tier')
    message = Field(ChannelSubscriptionMessage)

    @property
    def tier(self):
        return int(self._tier.replace('0', '', -1))


class HypeTrainContribution(SlottedModel):
    user_id = Field(text)
    user_login = Field(text)
    user_name = Field(text)
    # TODO: 3nUm!!!
    type = Field(text)
    total = Field(int)

    @property
    def user(self):
        return User.create(data={"id": self.user_id, "login": self.user_login,
                                 "name": self.user_name})


class HypeTrain(SlottedModel):
    id = Field(text)
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    total = Field(int)
    progress = Field(int)
    goal = Field(int)
    top_contributions = Field(HypeTrainContribution)
    last_contribution = Field(HypeTrainContribution)
    level = Field(text)
    started_at = Field(datetime)
    expires_at = Field(datetime, create=False)
    ended_at = Field(datetime, create=False)
    cooldown_ends_at = Field(datetime, create=False)

    @property
    def broadcaster(self):
        return User.create(data={"id": self.broadcaster_user_id, "login": self.broadcaster_user_login,
                                 "name": self.broadcaster_user_name})

