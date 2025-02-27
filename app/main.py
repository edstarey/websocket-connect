import json
import os
import urllib.request
import jwt
from jwt.algorithms import RSAAlgorithm

COGNITO_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
COGNITO_REGION = os.environ['AWS_REGION']
JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_POOL_ID}/.well-known/jwks.json"
jwks_cache = None

def lambda_handler(event, context):
    # 1. Get token from query params
    token = event.get("queryStringParameters", {}).get("token", "")
    if not token:
        print("No token provided")
        raise Exception("Unauthorized")

    # Remove "Bearer " prefix if present
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1]

    # 2. Verify JWT using Cognito JWKS
    global jwks_cache
    if jwks_cache is None:
        with urllib.request.urlopen(JWKS_URL) as response:
            jwks_cache = json.load(response)

    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header['kid']
        key = next(item for item in jwks_cache['keys'] if item["kid"] == kid)
    except Exception as e:
        print("Token kid not found in JWKS:", e)
        raise Exception("Unauthorized")

    public_key = RSAAlgorithm.from_jwk(json.dumps(key))
    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=[key["alg"]],  # e.g. RS256
            audience=os.environ['COGNITO_APP_CLIENT_ID'],  # must match your App Client ID
            issuer=f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_POOL_ID}"
        )
    except Exception as err:
        print("JWT verification failed:", err)
        raise Exception("Unauthorized")

    # 3. Build allow policy with context
    principal_id = claims.get("sub") or "user"
    return {
        "isAuthorized": True,
        "principalId": principal_id,
        "context": {
            "username": claims.get("cognito:username", ""),
            "sub": claims.get("sub", "")
        }
    }