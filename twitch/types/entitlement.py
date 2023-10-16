from twitch.types.base import SlottedModel, Field, text, datetime
from twitch.types.user import User


class DropEntitlementData(SlottedModel):
    organization_id = Field(text)
    category_id = Field(text)
    category_name = Field(text)
    campaign_id = Field(text)
    user_id = Field(text)
    user_name = Field(text)
    user_login = Field(text)
    entitlement_id = Field(text)
    benefit_id = Field(text)
    created_at = Field(datetime)

    @property
    def user(self):
        return User.create(data={"id": self.user_id, "login": self.user_login,
                                 "name": self.user_name})

