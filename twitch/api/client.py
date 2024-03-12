from contextlib import contextmanager

from twitch.util.functional import optional

try:
    import ujson as json
except ImportError:
    import json

from gevent.local import local

from twitch.api.http import HTTPClient, Routes
from twitch.util.logging import LoggingClass


class Responses(list):
    def rate_limited_duration(self):
        return sum(i.rate_limited_duration for i in self)

    @property
    def rate_limited(self):
        return self.rate_limited_duration() != 0


class APIClient(LoggingClass):
    """
    An abstraction over a :class:`twitch.api.http.HTTPClient`, which composes
    requests from provided data, and fits models with the returned data. The APIClient
    is the only path to the API used within models/other interfaces, and it's
    the recommended path for all third-party users/implementations.

    Parameters
    ----------
    client : Optional[:class:`twitch.client.Client`]
        The Twitch client this APIClient is a member of. This is used when constructing
        and fitting models from response data.

    Attributes
    ----------
    client : Optional[:class:`twitch.client.Client`]
        The Disco client this APIClient is a member of.
    http : :class:`disco.http.HTTPClient`
        The HTTPClient this APIClient uses for all requests.
    """

    def __init__(self, client=None, bot_user=None):
        # TODO: Twitch-ify
        # TODO: Create objects for all the return types...
        super(APIClient, self).__init__()

        self.client = client
        self.bot_user = bot_user
        self.http = HTTPClient(self._after_requests)

        self._captures = local()

    def _after_requests(self, response):
        if not hasattr(self._captures, 'responses'):
            return

        self._captures.responses.append(response)

    @contextmanager
    def capture(self):
        """
        Context manager which captures all requests made, returning a special
        `Responses` list, which can be used to introspect raw API responses. This
        method is a low-level utility which should only be used by experienced users.
        """
        responses = Responses()
        self._captures.responses = responses

        try:
            yield responses
        finally:
            delattr(self._captures, 'responses')

    def oauth_user_get(self, access_token=None):
        if access_token is None:
            return  # :(

        r = self.http(Routes.OAUTH_VALIDATE_TOKEN,
                      headers={"Authorization": f"OAuth {access_token}"})

        # TODO: Return OAuth user obj
        if r.status_code == 401:
            return None
        else:
            return r.json()

    def oauth_refresh_token(self, refresh_token):
        r = self.http(Routes.OAUTH_POST_TOKEN, params={
            "client_id": self.client.config.client_id,
            "client_secret": self.client.config.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        })

        if r.status_code == 401:
            return None
        else:
            return r.json()

    def eventsub_create_subscription(self, access_token, _type, version, condition, method='websocket', callback=None,
                                     secret=None, session_id=None, client_id=None, subscriptions=None):

        if subscriptions and isinstance(subscriptions, list):
            responses = {
                "success": [],
                "fails": []
            }
            for sub in subscriptions:
                payload = {
                    'type': sub["type"],
                    'version': sub["version"],
                    'condition': sub["condition"],
                    'transport': {}
                }

                if sub['method']:
                    payload['transport']['method'] = sub['method']
                if sub['callback']:
                    payload['transport']['callback'] = sub['callback']
                if sub['secret']:
                    payload['transport']['secret'] = sub['secret']
                if sub['session_id']:
                    payload['transport']['session_id'] = sub['session_id']

                r = self.http(Routes.CREATE_EVENTSUB_SUBSCRIPTION,
                              json=payload,
                              headers={
                                  'Authorization': f'Bearer {sub["access_token"]}',
                                  'Client-Id': f'{sub["client_id"] or self.client.config.client_id}'
                              })

                if r.status_code in [400, 401, 403, 409, 429]:
                    responses['fails'].append(r.json())
                elif r.status_code == 202:
                    responses['success'].append(r.json())

            return responses

        else:
            r = self.http(Routes.CREATE_EVENTSUB_SUBSCRIPTION,
                          headers={
                              'Authorization': f'Bearer {access_token}',
                              'Client-Id': f'{client_id or self.client.config.client_id}'
                          },
                          payload={
                              'type': _type,
                              'version': version,
                              'condition': condition,
                              'transport': optional(
                                  method=method,
                                  callback=callback,
                                  secret=secret,
                                  session_id=session_id
                              )
                          })

            print(r.status_code)
            print((r.json()))
            return r.json()

    def eventsub_get_subscriptions(self, access_token, status=None, _type=None, user_id=None, after=None, client_id=None):
        r = self.http(Routes.GET_EVENTSUB_SUBSCRIPTION,
                      headers={
                          'Authorization': f'Bearer {access_token}',
                          'Client-Id': f'{client_id or self.client.config.client_id}'
                      },
                      params=optional(
                          status=status,
                          type=_type,
                          user_id=user_id,
                          after=after
                      ))

        print(r.status_code)
        print(r.json())
        return r.json()

    def channels_commercial_start(self, broadcaster, length, auth=None):
        pass
