import json
import urllib.request
import pytest
import jwt
from jwt.algorithms import RSAAlgorithm
from app.main import lambda_handler, conn_table


# --- Helper Classes and Dummy Functions ---

class DummyResponse:
    def __init__(self, data):
        self.data = data.encode('utf-8')

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


def dummy_urlopen(url):
    dummy_jwks = {
        "keys": [{
            "kid": "test_kid",
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "n": "dummy_n",
            "e": "AQAB"
        }]
    }
    return DummyResponse(json.dumps(dummy_jwks))


def dummy_from_jwk(jwk_str):
    return "dummy_public_key"


def dummy_get_unverified_header(token):
    return {"kid": "test_kid"}


def dummy_jwt_decode(token, key, algorithms, audience):
    return {
        "sub": "user123",
        "cognito:username": "testuser",
        "aud": audience
    }


def dummy_jwt_decode_fail(token, key, algorithms, audience):
    raise Exception("Invalid token")


def dummy_put_item_success(Item):
    return {}


def dummy_put_item_fail(Item):
    raise Exception("DB error")


# --- Tests ---

def test_no_token(monkeypatch):
    event = {
        "headers": {},
        "queryStringParameters": {},
        "requestContext": {"connectionId": "conn1"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }
    with pytest.raises(Exception, match="Unauthorized"):
        lambda_handler(event, None)


def test_valid_token_header(monkeypatch):
    event = {
        "headers": {"Authorization": "Bearer dummy_token"},
        "requestContext": {"connectionId": "conn1"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }
    monkeypatch.setattr(urllib.request, "urlopen", dummy_urlopen)
    monkeypatch.setattr(RSAAlgorithm, "from_jwk", dummy_from_jwk)
    monkeypatch.setattr(jwt, "get_unverified_header", dummy_get_unverified_header)
    monkeypatch.setattr(jwt, "decode", dummy_jwt_decode)
    monkeypatch.setattr(conn_table, "put_item", dummy_put_item_success)

    result = lambda_handler(event, None)
    assert result["principalId"] == "user123"
    assert result["policyDocument"]["Statement"][0]["Resource"] == event["methodArn"]
    assert result["context"]["username"] == "testuser"


def test_valid_token_query_param(monkeypatch):
    # Updated key from 'authToken' to 'token'
    event = {
        "queryStringParameters": {"token": "dummy_token"},
        "requestContext": {"connectionId": "conn2"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }
    monkeypatch.setattr(urllib.request, "urlopen", dummy_urlopen)
    monkeypatch.setattr(RSAAlgorithm, "from_jwk", dummy_from_jwk)
    monkeypatch.setattr(jwt, "get_unverified_header", dummy_get_unverified_header)
    monkeypatch.setattr(jwt, "decode", dummy_jwt_decode)
    monkeypatch.setattr(conn_table, "put_item", dummy_put_item_success)

    result = lambda_handler(event, None)
    assert result["principalId"] == "user123"
    assert result["policyDocument"]["Statement"][0]["Resource"] == event["methodArn"]
    assert result["context"]["username"] == "testuser"


def test_invalid_jwt(monkeypatch):
    event = {
        "headers": {"Authorization": "Bearer dummy_token"},
        "requestContext": {"connectionId": "conn3"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }
    monkeypatch.setattr(urllib.request, "urlopen", dummy_urlopen)
    monkeypatch.setattr(RSAAlgorithm, "from_jwk", dummy_from_jwk)
    monkeypatch.setattr(jwt, "get_unverified_header", dummy_get_unverified_header)
    monkeypatch.setattr(jwt, "decode", dummy_jwt_decode_fail)

    with pytest.raises(Exception, match="Unauthorized"):
        lambda_handler(event, None)


def test_db_failure(monkeypatch):
    event = {
        "headers": {"Authorization": "Bearer dummy_token"},
        "requestContext": {"connectionId": "conn4"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }
    monkeypatch.setattr(urllib.request, "urlopen", dummy_urlopen)
    monkeypatch.setattr(RSAAlgorithm, "from_jwk", dummy_from_jwk)
    monkeypatch.setattr(jwt, "get_unverified_header", dummy_get_unverified_header)
    monkeypatch.setattr(jwt, "decode", dummy_jwt_decode)
    monkeypatch.setattr(conn_table, "put_item", dummy_put_item_fail)

    with pytest.raises(Exception, match="Unauthorized"):
        lambda_handler(event, None)