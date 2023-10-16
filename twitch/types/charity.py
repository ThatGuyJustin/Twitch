from twitch.types.base import SlottedModel, Field, text


class CharityDonationAmount(SlottedModel):
    value = Field(int)
    decimal_places = Field(int)
    currency = Field(text)


class Charity(SlottedModel):
    id = Field(text)
    campaign_id = Field(text)
    broadcaster_user_id = Field(int)
    broadcaster_user_login = Field(text)
    broadcaster_user_name = Field(text)
    charity_name = Field(text)
    charity_description = Field(text)
    charity_logo = Field(text)
    charity_website = Field(text)
