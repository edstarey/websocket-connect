import json
import pytest
import urllib.request
import jwt
from jwt.algorithms import RSAAlgorithm
from unittest.mock import patch

from app.main import lambda_handler

# Dummy JWKS data
DUMMY_JWKS = {
    "keys": [{
        "kid": "test_kid",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "n": "dummy_n",
        "e": "AQAB"
    }]
}

###############################
# Mocks / Helper Functions
###############################
class DummyResponse:
    """Simulates the response object returned by urllib.request.urlopen."""
    def __init__(self, data):
        self.data = data.encode('utf-8')
    def read(self):
        return self.data
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        pass

def mock_urlopen(url):
    """Mock urlopen that returns our dummy JWKS JSON."""
    return DummyResponse(json.dumps(DUMMY_JWKS))

def mock_get_unverified_header(token):
    """Pretend all tokens have kid=test_kid in the header."""
    return {"kid": "test_kid"}

def mock_from_jwk(jwk_str):
    """Return a placeholder public key object."""
    return "dummy_public_key"

def mock_jwt_decode_success(token, key, algorithms, audience, issuer):
    """Return a fake claims dict to simulate successful decode."""
    return {
        "sub": "user123",
        "cognito:username": "testuser",
        "aud": audience,
        # 'iss' matches the issuer, so no error
    }

def mock_jwt_decode_fail(token, key, algorithms, audience, issuer):
    """Always raise an exception to simulate invalid token."""
    raise Exception("Invalid token")

###############################
# Pytest Test Cases
###############################
@patch.object(urllib.request, "urlopen", side_effect=mock_urlopen)
def test_no_token(mock_url):
    """No token in query params -> Unauthorized"""
    event = {
        "queryStringParameters": {},
        "requestContext": {"connectionId": "conn1"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }
    with pytest.raises(Exception, match="Unauthorized"):
        lambda_handler(event, None)

@patch.object(urllib.request, "urlopen", side_effect=mock_urlopen)
@patch.object(RSAAlgorithm, "from_jwk", side_effect=mock_from_jwk)
@patch.object(jwt, "get_unverified_header", side_effect=mock_get_unverified_header)
@patch.object(jwt, "decode", side_effect=mock_jwt_decode_success)
def test_valid_token_query_param(mock_decode, mock_header, mock_from, mock_url):
    """Token in query param -> Should succeed"""
    event = {
        "queryStringParameters": {"token": "dummy_token"},
        "requestContext": {"connectionId": "conn2"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }
    result = lambda_handler(event, None)
    assert result["isAuthorized"] is True
    assert result["principalId"] == "user123"
    assert result["context"]["username"] == "testuser"

@patch.object(urllib.request, "urlopen", side_effect=mock_urlopen)
@patch.object(RSAAlgorithm, "from_jwk", side_effect=mock_from_jwk)
@patch.object(jwt, "get_unverified_header", side_effect=mock_get_unverified_header)
@patch.object(jwt, "decode", side_effect=mock_jwt_decode_fail)
def test_invalid_jwt(mock_decode, mock_header, mock_from, mock_url):
    """Invalid token -> Unauthorized"""
    event = {
        "queryStringParameters": {"token": "dummy_token"},
        "requestContext": {"connectionId": "conn4"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }
    with pytest.raises(Exception, match="Unauthorized"):
        lambda_handler(event, None)