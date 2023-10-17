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
    API_BASE_URL = "https://api.twitch.tv/helix"
    OAUTH_BASE_URL = "https://id.twitch.tv"


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
        :class:`disco.api.http.Routes`) with a set of URL arguments, and keyword
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
