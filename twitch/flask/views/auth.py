from flask import Blueprint
from requests_oauthlib import OAuth2Session

Auth = Blueprint('auth', __name__, url_prefix='/internal/auth')