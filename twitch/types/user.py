from twitch.types.base import SlottedModel, text, Field


class User(SlottedModel):
    id = Field(int)
    login = Field(text)
    name = Field(text)
