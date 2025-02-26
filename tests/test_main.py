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
    # Return a dummy JWKS response with a key matching "test_kid"
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
    # Return a dummy public key (actual value irrelevant because we patch jwt.decode)
    return "dummy_public_key"

def dummy_get_unverified_header(token):
    return {"kid": "test_kid"}

def dummy_jwt_decode(token, key, algorithms, audience):
    # Return dummy claims matching the expected audience and including user info
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
    # Test event with no token provided (neither header nor query string)
    event = {
        "headers": {},
        "queryStringParameters": {},
        "requestContext": {"connectionId": "conn1"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }
    with pytest.raises(Exception, match="Unauthorized"):
        lambda_handler(event, None)

def test_valid_token_header(monkeypatch):
    # Test valid token provided in Authorization header
    event = {
        "headers": {"Authorization": "Bearer dummy_token"},
        "requestContext": {"connectionId": "conn1"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }

    # Patch external calls and dependencies
    monkeypatch.setattr(urllib.request, "urlopen", dummy_urlopen)
    monkeypatch.setattr(RSAAlgorithm, "from_jwk", dummy_from_jwk)
    monkeypatch.setattr(jwt, "get_unverified_header", dummy_get_unverified_header)
    monkeypatch.setattr(jwt, "decode", dummy_jwt_decode)
    monkeypatch.setattr(conn_table, "put_item", dummy_put_item_success)

    result = lambda_handler(event, None)

    # Verify that the returned policy contains the expected values.
    assert result["principalId"] == "user123"
    assert result["policyDocument"]["Statement"][0]["Resource"] == event["methodArn"]
    assert result["context"]["username"] == "testuser"

def test_valid_token_query_param(monkeypatch):
    # Test valid token provided as a query parameter (using 'authToken')
    event = {
        "queryStringParameters": {"authToken": "dummy_token"},
        "requestContext": {"connectionId": "conn2"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }

    # Patch external calls and dependencies as before
    monkeypatch.setattr(urllib.request, "urlopen", dummy_urlopen)
    monkeypatch.setattr(RSAAlgorithm, "from_jwk", dummy_from_jwk)
    monkeypatch.setattr(jwt, "get_unverified_header", dummy_get_unverified_header)
    monkeypatch.setattr(jwt, "decode", dummy_jwt_decode)
    monkeypatch.setattr(conn_table, "put_item", dummy_put_item_success)

    result = lambda_handler(event, None)

    # Check returned policy details.
    assert result["principalId"] == "user123"
    assert result["policyDocument"]["Statement"][0]["Resource"] == event["methodArn"]
    assert result["context"]["username"] == "testuser"

def test_invalid_jwt(monkeypatch):
    # Test scenario where jwt.decode fails (invalid token)
    event = {
        "headers": {"Authorization": "Bearer dummy_token"},
        "requestContext": {"connectionId": "conn3"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }

    monkeypatch.setattr(urllib.request, "urlopen", dummy_urlopen)
    monkeypatch.setattr(RSAAlgorithm, "from_jwk", dummy_from_jwk)
    monkeypatch.setattr(jwt, "get_unverified_header", dummy_get_unverified_header)
    # Force jwt.decode to fail
    monkeypatch.setattr(jwt, "decode", dummy_jwt_decode_fail)

    with pytest.raises(Exception, match="Unauthorized"):
        lambda_handler(event, None)

def test_db_failure(monkeypatch):
    # Test scenario where storing the connection fails (e.g., DynamoDB error)
    event = {
        "headers": {"Authorization": "Bearer dummy_token"},
        "requestContext": {"connectionId": "conn4"},
        "methodArn": "arn:aws:execute-api:region:acct:apiId/stage/$connect"
    }

    monkeypatch.setattr(urllib.request, "urlopen", dummy_urlopen)
    monkeypatch.setattr(RSAAlgorithm, "from_jwk", dummy_from_jwk)
    monkeypatch.setattr(jwt, "get_unverified_header", dummy_get_unverified_header)
    monkeypatch.setattr(jwt, "decode", dummy_jwt_decode)
    # Simulate DB failure on put_item
    monkeypatch.setattr(conn_table, "put_item", dummy_put_item_fail)

    with pytest.raises(Exception, match="Unauthorized"):
        lambda_handler(event, None)