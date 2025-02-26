import os
import json
import logging
import urllib.request

import jwt  # PyJWT
from jwt.algorithms import RSAAlgorithm
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load config from env
USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
APP_CLIENT_ID = os.environ['COGNITO_APP_CLIENT_ID']
DDB_TABLE = os.environ['CONNECTIONS_TABLE']

# Use the AWS_REGION environment variable (or default to 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
conn_table = dynamodb.Table(DDB_TABLE)

# Cache JWKS to avoid repeated network calls
_jwks_cache = None

def lambda_handler(event, context):
    token = None
    # Accept token from either Authorization header or query string
    if event.get('headers') and event['headers'].get('Authorization'):
        auth_header = event['headers']['Authorization']
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
    if not token and event.get('queryStringParameters'):
        token = event['queryStringParameters'].get('authToken') or event['queryStringParameters'].get('token')
    if not token:
        logger.warning("No JWT token found in connect request")
        raise Exception("Unauthorized")  # triggers 401

    try:
        # Load JWKS (JSON Web Key Set) for our Cognito User Pool
        global _jwks_cache
        if not _jwks_cache:
            jwks_url = f"https://cognito-idp.{os.environ['AWS_REGION']}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
            with urllib.request.urlopen(jwks_url) as response:
                _jwks_cache = json.loads(response.read())['keys']
        # Find the public key for this token's kid
        headers = jwt.get_unverified_header(token)
        key_matches = [k for k in _jwks_cache if k["kid"] == headers.get("kid")]
        if not key_matches:
            raise Exception("Unauthorized")  # Unknown key ID
        public_key = RSAAlgorithm.from_jwk(json.dumps(key_matches[0]))
        # Verify JWT signature, expiration, audience, etc.
        claims = jwt.decode(token, public_key, algorithms=['RS256'], audience=APP_CLIENT_ID)
        user_id = claims.get('sub')  # Cognito user unique ID
        username = claims.get('cognito:username') or claims.get('email') or user_id
    except Exception as e:
        logger.error(f"JWT validation failed: {e}")
        raise Exception("Unauthorized")

    # Store the connection
    connection_id = event['requestContext']['connectionId']
    try:
        conn_table.put_item(Item={
            'UserId': user_id,
            'ConnectionId': connection_id
        })
        logger.info(f"Stored connection {connection_id} for user {user_id}")
    except Exception as db_err:
        logger.error(f"Failed to store connection: {db_err}")
        raise Exception("Unauthorized")

    # Build an IAM policy to allow the connection
    principal_id = user_id
    method_arn = event.get('methodArn')
    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": "Allow",
                "Resource": method_arn
            }]
        },
        "context": {
            "username": username
        }
    }
    return policy