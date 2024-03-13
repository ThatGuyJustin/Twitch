import platform
import random

import gevent
import requests

from requests import __version__ as requests_version
from twitch import VERSION as twitchpy_version
from twitch.api.ratelimit import RateLimiter
from twitch.util.logging import LoggingClass


class HTTPMethod:
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'


def random_backoff():
    """
    Returns a random backoff (in milliseconds) to be used for any error the
    client suspects is transient. Will always return a value between 500 and
    5000 milliseconds.

    :returns: a random backoff in milliseconds.
    :rtype: float
    """
    return random.randint(500, 5000) / 1000.0


class Routes:
    """
    Simple Python object-enum of all method/url route combinations available to
    this client.
    """
    # Twitch separates out its Auth from its main API :')
    API_BASE_URL = "https://api.twitch.tv/helix"
    OAUTH_BASE_URL = "https://id.twitch.tv"

    # Channel related endpoints
    CHANNEL_BASE = API_BASE_URL + "/channels"
    START_COMMERCIAL = (HTTPMethod.POST, CHANNEL_BASE + "/commercial")
    GET_CHANNEL_INFORMATION = (HTTPMethod.GET, CHANNEL_BASE)
    MODIFY_CHANNEL_INFORMATION = (HTTPMethod.PATCH, CHANNEL_BASE)
    GET_CHANNEL_EDITORS = (HTTPMethod.GET, CHANNEL_BASE + "/editors")
    GET_FOLLOWED_CHANNELS = (HTTPMethod.GET, CHANNEL_BASE + "/followed")
    GET_CHANNEL_FOLLOWERS = (HTTPMethod.GET, CHANNEL_BASE + "/followers")
    GET_CHANNEL_VIPS = (HTTPMethod.GET, CHANNEL_BASE + "/vips")
    ADD_CHANNEL_VIP = (HTTPMethod.POST, CHANNEL_BASE + "/vips")
    REMOVE_CHANNEL_VIP = (HTTPMethod.DELETE, CHANNEL_BASE + "/vips")

    # Analytic related endpoints
    ANALYTICS_BASE = API_BASE_URL + "/analytics"
    EXTENSION_ANALYTICS = (HTTPMethod.GET, ANALYTICS_BASE + "/extensions")
    GAME_ANALYTICS = (HTTPMethod.GET, ANALYTICS_BASE + "/games")

    # Bit related endpoints
    BITS_BASE = API_BASE_URL + "/bits"
    BITS_LEADERBOARD = (HTTPMethod.GET, BITS_BASE + "/leaderboard")
    CHEERMOTES = (HTTPMethod.GET, BITS_BASE + "/cheermotes")
    GET_EXTENSION_BITS_PRODUCTS = (HTTPMethod.GET, BITS_BASE + "/extensions")
    UPDATE_EXTENSION_BITS_PRODUCTS = (HTTPMethod.PUT, BITS_BASE + "/extensions")

    # Extensions related endpoints
    EXTENSIONS_BASE = API_BASE_URL + "/extensions"
    EXTENSION_TRANSACTIONS = (HTTPMethod.GET, EXTENSIONS_BASE + "/transactions")
    GET_EXTENSION_CONFIGURATION_SEGMENT = (HTTPMethod.GET, EXTENSIONS_BASE + "/configurations")
    UPDATE_EXTENSION_CONFIGURATION_SEGMENT = (HTTPMethod.PUT, EXTENSIONS_BASE + "/configurations")
    UPDATE_EXTENSION_CONFIGURATION_REQUIRED = (HTTPMethod.PUT, EXTENSIONS_BASE + "/required_configuration")
    SEND_EXTENSION_PUBSUB_MESSAGE = (HTTPMethod.POST, EXTENSIONS_BASE + "/pubsub")
    GET_EXTENSION_LIVE_CHANNELS = (HTTPMethod.GET, EXTENSIONS_BASE + "/live")
    GET_EXTENSION_SECRETS = (HTTPMethod.GET, EXTENSIONS_BASE + "/jwt/secrets")
    CREATE_EXTENSION_SECRETS = (HTTPMethod.POST, EXTENSIONS_BASE + "/jwt/secrets")
    SEND_EXTENSION_CHAT_MESSAGE = (HTTPMethod.POST, EXTENSIONS_BASE + "/chat")
    GET_EXTENSIONS = (HTTPMethod.GET, EXTENSIONS_BASE)
    GET_RELEASED_EXTENSIONS = (HTTPMethod.GET, EXTENSIONS_BASE + "/released")

    # Channel point related endpoints
    POINTS_BASE = API_BASE_URL + "/channel_points"
    CREATE_CUSTOM_REWARD = (HTTPMethod.POST, POINTS_BASE + "/custom_rewards")
    DELETE_CUSTOM_REWARD = (HTTPMethod.DELETE, POINTS_BASE + "/custom_rewards")
    GET_CUSTOM_REWARD = (HTTPMethod.GET, POINTS_BASE + "/custom_rewards")
    UPDATE_CUSTOM_REWARD = (HTTPMethod.PATCH, POINTS_BASE + "/custom_rewards")
    GET_CUSTOM_REWARD_REDEMPTION = (HTTPMethod.GET, POINTS_BASE + "/custom_rewards/redemptions")
    UPDATE_CUSTOM_REWARD_REDEMPTION = (HTTPMethod.GET, POINTS_BASE + "/custom_rewards/redemptions")

    # Charity related endpoints
    CHARITY_BASE = API_BASE_URL + "/charity"
    GET_CHARITY_CAMPAIGN = (HTTPMethod.GET, CHARITY_BASE + "/campaigns")
    GET_CHARITY_DONATIONS = (HTTPMethod.GET, CHARITY_BASE + "/donations")

    # Chat related endpoints
    CHAT_BASE = API_BASE_URL + "/chat"
    GET_CHATTERS = (HTTPMethod.GET, CHAT_BASE + "/chatters")
    GET_CHANNEL_EMOTES = (HTTPMethod.GET, CHAT_BASE + "/emotes")
    GET_GLOBAL_EMOTES = (HTTPMethod.GET, CHAT_BASE + "/emotes/global")
    GET_EMOTE_SETS = (HTTPMethod.GET, CHAT_BASE + "/emotes/set")
    GET_CHANNEL_CHAT_BADGES = (HTTPMethod.GET, CHAT_BASE + "/badges")
    GET_GLOBAL_CHAT_BADGES = (HTTPMethod.GET, CHAT_BASE + "/badges/global")
    GET_CHAT_SETTINGS = (HTTPMethod.GET, CHAT_BASE + "/settings")
    UPDATE_CHAT_SETTINGS = (HTTPMethod.PATCH, CHAT_BASE + "/settings")
    POST_CHAT_ANNOUNCEMENT = (HTTPMethod.POST, CHAT_BASE + "/announcements")
    POST_CHAT_SHOUTOUT = (HTTPMethod.POST, CHAT_BASE + "/shoutouts")
    GET_USER_CHAT_COLOR = (HTTPMethod.GET, CHAT_BASE + "/color")
    UPDATE_USER_CHAT_COLOR = (HTTPMethod.PUT, CHAT_BASE + "/color")

    # Clips related endpoints
    CLIPS_BASE = API_BASE_URL + "/clips"
    CREATE_CLIP = (HTTPMethod.POST, CLIPS_BASE)
    GET_CLIP = (HTTPMethod.GET, CLIPS_BASE)

    # Content Classifications labels
    GET_CONTENT_CLASSIFICATION_LABELS = (HTTPMethod.GET, API_BASE_URL + "/content_classification_labels")

    # Drop related endpoints
    GET_DROPS_ENTITLEMENTS = (HTTPMethod.GET, API_BASE_URL + "/entitlements/drops")
    UPDATE_DROPS_ENTITLEMENTS = (HTTPMethod.PATCH, API_BASE_URL + "/entitlements/drops")

    # Eventsub related endpoints
    EVENTSUB_BASE = API_BASE_URL + "/eventsub"
    CREATE_EVENTSUB_SUBSCRIPTION = (HTTPMethod.POST, EVENTSUB_BASE + "/subscriptions")
    # UPDATE_PUBSUB_SUBSCRIPTION = (HTTPMethod.PATCH, PUBSUB_BASE + "/subscriptions")
    DELETE_EVENTSUB_SUBSCRIPTION = (HTTPMethod.DELETE, EVENTSUB_BASE + "/subscriptions")
    GET_EVENTSUB_SUBSCRIPTION = (HTTPMethod.GET, EVENTSUB_BASE + "/subscriptions")

    # Games related endpoints
    GAMES_BASE = API_BASE_URL + "/games"
    GET_TOP_GAMES = (HTTPMethod.GET, GAMES_BASE + "/top")
    GET_GAMES = (HTTPMethod.GET, GAMES_BASE)

    # Goals
    GOALS_BASE = API_BASE_URL + "/goals"
    GET_CREATOR_GOALS = (HTTPMethod.GET, GOALS_BASE)

    # Guest star related endpoints
    GUEST_STAR_BASE = API_BASE_URL + "/guest_star"
    GET_CHANNEL_GUEST_STAR_SETTINGS = (HTTPMethod.GET, GUEST_STAR_BASE + "/channel_settings")
    UPDATE_CHANNEL_GUEST_STAR_SETTINGS = (HTTPMethod.PUT, GUEST_STAR_BASE + "/channel_settings")
    GET_GUEST_STAR_SESSION = (HTTPMethod.GET, GUEST_STAR_BASE + "/session")
    CREATE_GUEST_STAR_SESSION = (HTTPMethod.POST, GUEST_STAR_BASE + "/session")
    END_GUEST_STAR_SESSION = (HTTPMethod.DELETE, GUEST_STAR_BASE + "/session")
    GET_GUEST_STAR_INVITES = (HTTPMethod.GET, GUEST_STAR_BASE + "/invites")
    SEND_GUEST_STAR_INVITE = (HTTPMethod.POST, GUEST_STAR_BASE + "/invites")
    DELETE_GUEST_STAR_INVITE = (HTTPMethod.DELETE, GUEST_STAR_BASE + "/invites")
    ASSIGN_GUEST_STAR_SLOT = (HTTPMethod.POST, GUEST_STAR_BASE + "/slot")
    UPDATE_GUEST_STAR_SLOT = (HTTPMethod.PATCH, GUEST_STAR_BASE + "/slot")
    DELETE_GUEST_STAR_SLOT = (HTTPMethod.DELETE, GUEST_STAR_BASE + "/slot")
    UPDATE_GUEST_STAR_SLOT_SETTINGS = (HTTPMethod.PATCH, GUEST_STAR_BASE + "/slot_settings")

    # Hypetrain
    HYPE_TRAIN_BASE = API_BASE_URL + "/hypetrain"
    GET_HYPE_TRAIN_EVENTS = (HTTPMethod.GET, HYPE_TRAIN_BASE + "/events")

    # Moderation related endpoints
    MODERATION_BASE = API_BASE_URL + "/moderation"
    CHECK_AUTOMOD_STATUS = (HTTPMethod.POST, MODERATION_BASE + "/enforcements/status")
    MANAGE_HELD_AUTOMOD_MESSAGES = (HTTPMethod.POST, MODERATION_BASE + "/automod/message")
    GET_AUTOMOD_SETTINGS = (HTTPMethod.GET, MODERATION_BASE + "/automod/settings")
    UPDATE_AUTOMOD_SETTINGS = (HTTPMethod.PUT, MODERATION_BASE + "/automod/settings")
    GET_BANNED_USERS = (HTTPMethod.GET, MODERATION_BASE + "/banned")
    BAN_USER = (HTTPMethod.POST, MODERATION_BASE + "/bans")
    UNBAN_USER = (HTTPMethod.DELETE, MODERATION_BASE + "/bans")
    GET_BLOCKED_TERMS = (HTTPMethod.GET, MODERATION_BASE + "/blocked_terms")
    ADD_BLOCKED_TERM = (HTTPMethod.POST, MODERATION_BASE + "/blocked_terms")
    REMOVE_BLOCKED_TERM = (HTTPMethod.DELETE, MODERATION_BASE + "/blocked_terms")
    DELETE_CHAT_MESSAGES = (HTTPMethod.DELETE, MODERATION_BASE + "/chat")
    GET_MODERATORS = (HTTPMethod.GET, MODERATION_BASE + "/moderators")
    ADD_MODERATORS = (HTTPMethod.POST, MODERATION_BASE + "/moderators")
    REMOVE_MODERATORS = (HTTPMethod.DELETE, MODERATION_BASE + "/moderators")
    UPDATE_SHIELD_MODE_STATUS = (HTTPMethod.PUT, MODERATION_BASE + "/shield_mode")
    GET_SHIELD_MODE_STATUS = (HTTPMethod.GET, MODERATION_BASE + "/shield_mode")

    # Polls endpoints
    POLLS_BASE = API_BASE_URL + "/polls"
    GET_POLLS = (HTTPMethod.GET, POLLS_BASE)
    CREATE_POLL = (HTTPMethod.POST, POLLS_BASE)
    END_POLL = (HTTPMethod.PATCH, POLLS_BASE)

    # Prediction Endpoints
    PREDICTIONS_BASE = API_BASE_URL + "/predictions"
    GET_PREDICTIONS = (HTTPMethod.GET, PREDICTIONS_BASE)
    CREATE_PREDICTION = (HTTPMethod.POST, PREDICTIONS_BASE)
    END_PREDICTION = (HTTPMethod.PATCH, PREDICTIONS_BASE)

    # Raid endpoints
    RAID_BASE = API_BASE_URL + "/raids"
    START_RAID = (HTTPMethod.POST, RAID_BASE)
    CANCEL_RAID = (HTTPMethod.DELETE, RAID_BASE)

    # Stream schedule endpoints
    STREAM_SCHEDULE_BASE = API_BASE_URL + "/schedule"
    GET_STREAM_SCHEDULE = (HTTPMethod.GET, STREAM_SCHEDULE_BASE)
    GET_ICALENDAR = (HTTPMethod.GET, STREAM_SCHEDULE_BASE + "/icalendar")
    UPDATE_STREAM_SCHEDULE = (HTTPMethod.PATCH, STREAM_SCHEDULE_BASE + "/settings")
    CREATE_STREAM_SCHEDULE_SEGMENT = (HTTPMethod.POST, STREAM_SCHEDULE_BASE + "/segment")
    UPDATE_STREAM_SCHEDULE_SEGMENT = (HTTPMethod.PATCH, STREAM_SCHEDULE_BASE + "/segment")
    DELETE_STREAM_SCHEDULE_SEGMENT = (HTTPMethod.DELETE, STREAM_SCHEDULE_BASE + "/segment")

    # Search endpoints
    SEARCH_CATEGORIES = (HTTPMethod.GET, API_BASE_URL + "/search/categories")
    SEARCH_CHANNELS = (HTTPMethod.GET, API_BASE_URL + "/search/channels")

    # Stream endpoints
    STREAMS_BASE = API_BASE_URL + "/streams"
    GET_STREAM_KEY = (HTTPMethod.GET, STREAMS_BASE + "/key")
    GET_STREAMS = (HTTPMethod.GET, STREAMS_BASE)
    GET_FOLLOWED_STREAMS = (HTTPMethod.GET, STREAMS_BASE + "/followed")
    CREATE_STREAM_MARKER = (HTTPMethod.POST, STREAMS_BASE + "/markers")
    GET_STREAM_MARKER = (HTTPMethod.GET, STREAMS_BASE + "/markers")
    GET_STREAM_TAGS = (HTTPMethod.GET, API_BASE_URL + "/streams/tags")

    # Subscription Endpoints
    GET_BROADCASTER_SUBSCRIPTIONS = (HTTPMethod.GET, API_BASE_URL + "/subscriptions")
    CHECK_USER_SUBSCRIPTION = (HTTPMethod.GET, API_BASE_URL + "/subscriptions/user")

    # Stream tags
    GET_ALL_STREAM_TAGS = (HTTPMethod.GET, API_BASE_URL + "/tags/streams")

    # Teams
    GET_CHANNEL_TEAMS = (HTTPMethod.GET, API_BASE_URL + "/teams/channel")
    GET_TEAMS = (HTTPMethod.GET, API_BASE_URL + "/teams")

    # User endpoints
    USER_BASE = API_BASE_URL + "/users"
    GET_USERS = (HTTPMethod.GET, USER_BASE)
    UPDATE_USER = (HTTPMethod.PUT, USER_BASE)
    GET_USER_BLOCK_LIST = (HTTPMethod.GET, USER_BASE + "/blocks")
    BLOCK_USER = (HTTPMethod.PUT, USER_BASE + "/blocks")
    UNBLOCK_USER = (HTTPMethod.DELETE, USER_BASE + "/blocks")
    GET_USER_EXTENSIONS = (HTTPMethod.GET, USER_BASE + "/extensions/list")
    GET_USER_ACTIVE_EXTENSIONS = (HTTPMethod.GET, USER_BASE + "/extensions")
    UPDATE_USER_EXTENSIONS = (HTTPMethod.PUT, USER_BASE + "/extensions")

    # Videos
    GET_VIDEOS = (HTTPMethod.GET, API_BASE_URL + "/videos")
    DELETE_VIDEOS = (HTTPMethod.DELETE, API_BASE_URL + "/videos")

    # Whisper
    SEND_WHISPER = (HTTPMethod.POST, API_BASE_URL + "/whispers")

    OAUTH_VALIDATE_TOKEN = (HTTPMethod.GET, OAUTH_BASE_URL + "/oauth2/validate")
    OAUTH_POST_TOKEN = (HTTPMethod.POST, OAUTH_BASE_URL + "/oauth2/token")
    OAUTH_AUTHORIZE_TOKEN = (HTTPMethod.GET, OAUTH_BASE_URL + "/oauth2/authorize")


class APIResponse:
    def __init__(self):
        self.response = None
        self.exception = None
        self.rate_limited_duration = 0


class APIException(Exception):
    """
    Exception thrown when an HTTP-client level error occurs. Usually this will
    be a non-success status-code, or a transient network issue.

    Attributes
    ----------
    status_code : int
        The status code returned by the API for the request that triggered this
        error.
    """
    def __init__(self, response, retries=None):
        self.response = response
        self.retries = retries

        self.code = 0
        self.msg = 'Request Failed ({})'.format(response.status_code)
        self.errors = {}

        if self.retries:
            self.msg += ' after {} retries'.format(self.retries)

        # Try to decode JSON, and extract params
        try:
            data = self.response.json()

            if 'code' in data:
                self.code = data['code']
                self.errors = data.get('errors', {})
                self.msg = '{} ({} - {})'.format(data['message'], self.code, self.errors)
            elif len(data) == 1:
                key, value = list(data.items())[0]
                if not isinstance(value, str):
                    value = ', '.join(value)
                self.msg = 'Request Failed: {}: {}'.format(key, value)
        except ValueError:
            pass

        # DEPRECATED: left for backwards compat
        self.status_code = response.status_code
        self.content = response.content

        super(APIException, self).__init__(self.msg)


class HTTPClient(LoggingClass):
    """
    A simple HTTP client which wraps the requests library, adding support for
    Discords rate-limit headers, authorization, and request/response validation.
    """
    MAX_RETRIES = 5

    def __init__(self, token, after_request=None):
        super(HTTPClient, self).__init__()

        py_version = platform.python_version()

        self.limiter = RateLimiter()
        self.after_request = after_request

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TwitchPy (https://github.com/ThatGuyJustin/Twitch {}) Python/{} requests/{}'.format(
                twitchpy_version,
                py_version,
                requests_version),
        })

        # if token:
        #     self.session.headers['Authorization'] = 'Bearer ' + token

    def __call__(self, route, args=None, **kwargs):
        return self.call(route, args, **kwargs)

    def call(self, route, args=None, **kwargs):
        """
        Makes a request to the given route (as specified in
        :class:`twitch.api.http.Routes`) with a set of URL arguments, and keyword
        arguments passed to requests.

        Parameters
        ----------
        route : tuple(:class:`HTTPMethod`, str)
            The method.URL combination that when compiled with URL arguments
            creates a requestable route which the HTTPClient will make the
            request too.
        args : dict(str, str)
            A dictionary of URL arguments that will be compiled with the raw URL
            to create the requestable route. The HTTPClient uses this to track
            rate limits as well.
        kwargs : dict
            Keyword arguments that will be passed along to the requests library.

        Raises
        ------
        APIException
            Raised when an unrecoverable error occurs, or when we've exhausted
            the number of retries.

        Returns
        -------
        :class:`requests.Response`
            The response object for the request.
        """
        args = args or {}
        retry = kwargs.pop('retry_number', 0)

        # Build the bucket URL
        args = {k: v for k, v in args.items()}
        filtered = {k: (v if k in ('guild', 'channel') else '') for k, v in args.items()}
        bucket = (route[0], route[1].format(**filtered))

        response = APIResponse()

        # Possibly wait if we're rate limited
        response.rate_limited_duration = self.limiter.check(bucket)

        self.log.debug('KW: %s', kwargs)

        # Make the actual request
        url = route[1].format(**args)
        self.log.info('%s %s %s', route[0], url, '({})'.format(kwargs.get('params')) if kwargs.get('params') else '')
        try:
            r = self.session.request(route[0], url, **kwargs)

            if self.after_request:
                response.response = r
                self.after_request(response)

            # Update rate limiter
            self.limiter.update(bucket, r)

            # If we got a success status code, just return the data
            if r.status_code < 400:
                return r
            elif r.status_code != 429 and 400 <= r.status_code < 500:
                self.log.warning('Request failed with code %s: %s', r.status_code, r.content)
                response.exception = APIException(r)
                raise response.exception
            elif r.status_code in [429, 500, 502, 503]:
                if r.status_code == 429:
                    self.log.warning('Request responded w/ 429, retrying (but this should not happen, check your clock sync)')

                # If we hit the max retries, throw an error
                retry += 1
                if retry > self.MAX_RETRIES:
                    self.log.error('Failing request, hit max retries')
                    raise APIException(r, retries=self.MAX_RETRIES)

                backoff = random_backoff()
                if r.status_code in [500, 502, 503]:
                    self.log.warning('Request to `{}` failed with code {}, retrying after {}s'.format(
                        url, r.status_code, backoff,
                    ))
                else:
                    self.log.warning('Request to `{}` failed with code {}, retrying after {}s ({})'.format(
                        url, r.status_code, backoff, r.content,
                    ))
                gevent.sleep(backoff)

                # Otherwise just recurse and try again
                return self(route, args, retry_number=retry, **kwargs)
        except ConnectionError:
            # Catch ConnectionResetError
            backoff = random_backoff()
            self.log.warning('Request to `{}` failed with ConnectionError, retrying after {}s'.format(url, backoff))
            gevent.sleep(backoff)
            return self(route, args, retry_number=retry, **kwargs)
        except requests.exceptions.Timeout:
            backoff = random_backoff()
            self.log.warning('Request to `{}` failed with ConnectionTimeout, retrying after {}s')
            gevent.sleep(backoff)
            return self(route, args, retry_number=retry, **kwargs)
