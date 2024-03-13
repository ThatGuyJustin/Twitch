import copy

import requests
from flask import Blueprint, session, redirect, request
from requests_oauthlib import OAuth2Session

from twitch.api.http import Routes


def InternalOauth(client, config):
    headers = copy.copy(requests.utils.default_headers())
    headers.update({"Client-ID": str(config.client_id)})

    def make_twitch_session(token=None, state=None, scope=None):
        # Need to add token for allow bot to do whatever
        return OAuth2Session(
            client_id=config.client_id,
            token=token,
            state=state,
            scope=scope,
            redirect_uri="/_auth/callback",
            auto_refresh_url=Routes.OAUTH_POST_TOKEN[1]
        )

    b = Blueprint('internalauth', __name__, root_path="/_auth")

    @b.route('/redirect')
    def twitchredirect():
        # Fix inscope
        twitch = make_twitch_session(scope=('user:read:subscriptions',))
        twitch.headers = headers
        auth_url, state = twitch.authorization_url(Routes.OAUTH_AUTHORIZE_TOKEN[1])
        session['oauth_state'] = state
        return redirect(auth_url)

    @b.route('/callback')
    def twitchcallback():
        if request.values.get('error'):
            return "an error has occurred", 500

        if 'oauth_state' not in session:
            return redirect('/_auth/redirect')

        code = request.args.get('code', '')
        twitch = make_twitch_session(state=session['oauth_state'])
        del session['oauth_state']

        twitch.headers = headers
        token = twitch.fetch_token(Routes.OAUTH_POST_TOKEN[1], client_secret=config.client_secret,
                                   authorization_response=request.url, code=code, include_client_id=True)
        # profit?
        return 'Sucessfully got token', 200

    return b
