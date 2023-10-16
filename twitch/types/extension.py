from twitch.types.base import SlottedModel, text, Field


class Product(SlottedModel):
    name = Field(text)
    bits = Field(int)
    sku = Field(text)
    in_development = Field(bool)
