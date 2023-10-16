try:
    import ujson as json
except ImportError:
    import json

from twitch.pubsub.encoding.base import BaseEncoder


class JSONEncoder(BaseEncoder):
    TYPE = 'json'

    @staticmethod
    def encode(obj):
        return json.dumps(obj)

    @staticmethod
    def decode(obj):
        return json.loads(obj)