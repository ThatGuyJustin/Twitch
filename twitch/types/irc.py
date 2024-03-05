import copy

from twitch.types.base import SlottedModel, Field, DictField, ListField


class IRCRawMessage(SlottedModel):
    prefix = Field(str)
    tags = DictField(str, value_type=str)
    command = Field(str)
    parameters = ListField(str)
    raw = Field(str)

    @classmethod
    def from_raw(cls, message: str):
        """
        Parse the message string from Twitch IIRC (IIRCv3)
        :param message: str
        :return: RawMessage
        """
        if not message:
            return None

        parts = message.split(' ')

        prefix = None
        tags = {}
        parameters = []

        if parts[0].startswith('@'):
            tags_str = parts.pop(0)[1:]
            tags_list = tags_str.split(';')
            tags = {tag.split('=')[0]: tag.split('=')[1] for tag in tags_list}

        # Parse prefix
        if parts[0].startswith(':'):
            prefix = parts.pop(0)[1:]

        # Parse command
        command = parts.pop(0)

        # Parse params
        while parts:
            if parts[0].startswith(':'):
                parameters.append(' '.join(parts)[1:].rstrip('\r\n'))
                break
            parameters.append(parts.pop(0).rstrip('\r\n'))
        return cls(prefix=prefix, tags=tags, command=command, parameters=parameters, raw=copy.copy(message))

    def to_json(self):
        to_deploy = {}

        if self.command == "GLOBALUSERSTATE":
            to_deploy['event_name'] = "ChatReady"

            chat_event = {
                "user_id": self.tags['user-id'],
                "badge_info": self.tags['badge-info'],
                "badges": self.tags['badges'],
                "color": self.tags['color'],
                "display_name": self.tags['display-name'],
                "username": self.tags['display-name'].lower(),
                "emote_sets": self.tags['emote-sets'].split(","),
                "user_type": self.tags['user-type']
            }

            to_deploy['event'] = chat_event

            return to_deploy

        if self.command == "PRIVMSG":
            to_deploy['event_name'] = "ChatMessageReceive"
            chat_event = {
                'id': self.tags['id'],
                'channel': self.parameters[0][1:],
                'broadcaster_id': self.tags['room-id'],
                'content': self.parameters[1],
                'emojis': {},
                'user': {
                    'id': self.tags['user-id'],
                    'username': self.prefix[:self.prefix.index("!")],
                    'display_name': self.tags['display-name'],
                    # TODO: Badges
                    'badges': None,
                    'chat_color': self.tags['color'],
                    'mod': int(self.tags['mod']),
                    'returning_chatter': int(self.tags['returning-chatter']),
                    'subscriber': int(self.tags['subscriber']),
                    'turbo': int(self.tags['turbo']),
                    'user_type': self.tags['user-type'],
                    'broadcaster': self.parameters[0][1:] == self.prefix[:self.prefix.index("!")]
                },
                'first_message': int(self.tags.get('first_message', 0)),
                'emote_only': int(self.tags.get('emote_only', 0))
            }

            if 'vip' in self.tags:
                chat_event['user']['vip'] = int(self.tags['vip'])

            to_deploy['event'] = chat_event

            return to_deploy
