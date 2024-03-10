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
                    'broadcaster': self.parameters[0][1:] == self.prefix[:self.prefix.index("!")],
                    'vip': int(self.tags.get('vip', 0))
                },
                'first_message': int(self.tags.get('first_message', 0)),
                'emote_only': int(self.tags.get('emote_only', 0)),
            }

            to_deploy['event'] = chat_event

            return to_deploy

        if self.command == "NOTICE":
            to_deploy['event_name'] = "ChatNotice"

            chat_event = {
                "id": self.tags.get("msg-id", None),
                "channel": self.parameters[0][1:],
                "message": self.parameters[1]
            }

            to_deploy['event'] = chat_event

            return to_deploy

        if self.command == "ROOMSTATE":
            to_deploy['event_name'] = "ChatRoomUpdate"

            chat_event = {
                'emote_only': int(self.tags.get('emote-only', 0)),
                'followers_only': int(self.tags.get('followers-only', -1)),
                'unique_only': int(self.tags.get('r9k', 0)),
                'channel': self.parameters[0][1:],
                'channel_id': int(self.tags.get("room-id", 0)),
                'slowmode': int(self.tags.get('slow', 0)),
                'sub_only': int(self.tags.get('subs-only', 0))
            }

            to_deploy['event'] = chat_event

            return to_deploy

        # TODO: BADGES????
        if self.command == "USERNOTICE":
            to_deploy['event_name'] = "ChatUserNotice"

            chat_event = {
                "id": self.tags["id"],
                "channel": self.parameters[1][1:],
                "channel_id": int(self.parameters.get("room-id", 0)),
                "message": self.parameters[0],
                "badge_info": self.tags.get("badge-info", None),
                "badges": self.tags.get("badges", None),
                "color": self.tags.get("color", None),
                "display_name": self.tags.get("display-name", None),
                "emotes": self.tags.get("emotes", None),
                "username": self.tags.get("login"),
                "mod": int(self.tags.get("mod", 0)),
                "msg_id": self.tags.get("msg-id", None),
                "subscriber": int(self.tags.get("subscriber", 0)),
                "system_msg": self.tags.get("system-msg", None),
                "tmi_timestamp": self.tags.get("tmi-sent-ts", None),
                "turbo": int(self.tags.get("turbo", 0)),
                "user_id": int(self.tags.get("user-id", 0)),
                "user_type": self.tags.get("user-type", "")
            }

            # TODO: Impliment extra notice thingys

            # TODO: Set separate events for things such as "ChatRaidMessage", "ChatSub", "ChatGiftSub"
            if self.tags.get("msg_id") and self.tags.get("msg_id") == "raid":
                chat_event['raid_broadcaster_displayname'] = self.tags.get("msg-param-displayName")
                chat_event['raid_broadcaster_login'] = self.tags.get("msg-param-login")
                chat_event['raiders_count'] = self.tags.get("msg-param-viewerCount")

            if self.tags.get("msg_id") and self.tags.get("msg_id") == "sub":
                pass

            if self.tags.get("msg_id") and self.tags.get("msg_id") == "resub":
                pass

            if self.tags.get("msg_id") and self.tags.get("msg_id") == "giftsub":
                pass

            if self.tags.get("msg_id") and self.tags.get("msg_id") == "anongiftpaidupgrade":
                pass

            if self.tags.get("msg_id") and self.tags.get("msg_id") == "giftpaidupgrade":
                pass

            if self.tags.get("msg_id") and self.tags.get("msg_id") == "ritual":
                pass

            if self.tags.get("msg_id") and self.tags.get("msg_id") == "bitsbadgetier":
                pass

            to_deploy['event'] = chat_event

            return to_deploy

        # TODO: Fix broken event. Due to twitch being wrong.
        if self.command == "WHISPER":
            # print(self.parameters)
            # print(self.tags)
            # print(self.raw)
            to_deploy['event_name'] = "ChatWhisper"

            chat_event = {
                'id': self.tags.get('message-id', None),
                'thread_id': self.tags.get('thread-id', None),
                'from_user': self.parameters[0],
                'to_user': self.prefix,
                'content': self.parameters[1],
                'badges': self.tags.get('badges', None),
                'color': self.tags.get('color', None),
                'display_name': self.tags.get('display-name', None),
                'emotes': self.tags.get('emotes', None),
                'user_id': int(self.tags.get('user-id', None)),
                'user_type': self.tags.get('user-type', "")
            }

            to_deploy['event'] = chat_event

            return to_deploy

        if self.command == "CLEARMSG":
            to_deploy['event_name'] = "ChatMessageDelete"

            chat_event = {
                'channel': self.parameters[0][1:],
                'channel_id': int(self.tags.get('room-id', 0)),
                'message': self.parameters[1],
                'user': self.tags.get('login', None),
                'message_id': self.tags.get('target-msg-id', None),
                'tmi_timestamp': self.tags.get('tmi-sent-ts', None)
            }

            to_deploy['event'] = chat_event

            return to_deploy

        # TODO: Test
        if self.command == "CLEARCHAT":
            to_deploy['event_name'] = "ChatMessageDelete"

            chat_event = {
                'channel': self.parameters[0][1:],
                'channel_id': int(self.tags.get('room-id', 0)),
                'user': self.parameters[1] if len(self.parameters) > 1 else None,
                'user_id': int(self.tags.get('target-user-id', 0)),
                'ban_duration': int(self.tags.get('ban-duration', -1)),
                'tmi_timestamp': self.tags.get('tmi-sent-ts', None)
            }

            to_deploy['event'] = chat_event

            return to_deploy

        if self.command == "JOIN" or self.command == "PART":
            to_deploy['event_name'] = f"ChatRoom{self.command.title()}"

            chat_event = {
                "user": self.prefix.split("!")[0],
                "channel": self.parameters[0][1:]
            }

            to_deploy['event'] = chat_event

            return to_deploy
