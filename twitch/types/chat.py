from twitch.types.base import SlottedModel, text, Field, DictField, ListField


class ChatBadge(SlottedModel):
    name = Field(text)
    value = Field(int)


class ChatEmoji(SlottedModel):
    name = Field(text)
    url = Field(text)


class ChatUser(SlottedModel):
    id = Field(int)
    username = Field(text)
    display_name = Field(text)
    badges = ListField(ChatBadge)
    chat_color = Field(text)
    mod = Field(bool)
    returning_chatter = Field(bool)
    subscriber = Field(bool)
    turbo = Field(bool)
    user_type = Field(text)
    vip = Field(bool, default=False)
    broadcaster = Field(bool)


# thefet4PetTheFethr -> :thefet4PetTheFethr:
class ChatMessage(SlottedModel):
    id = Field(text)
    channel = Field(text)
    broadcaster_id = Field(int)
    content = Field(text)
    emojis = DictField(text, ChatEmoji)
    user = Field(ChatUser)
    first_message = Field(bool)
    emote_only = Field(bool)

    def reply(self, content):
        # @reply-parent-msg-id=885196de-cb67-427a-baa8-82f9b0fcd05f PRIVMSG #lovingt3s :absolutely!
        self.client.irc.send(f"@reply-parent-msg-id={self.id} PRIVMSG #{self.channel} :{content}")

    def send_message(self, content):
        self.client.irc.send(f"PRIVMSG #{self.channel} :{content}")

