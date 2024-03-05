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