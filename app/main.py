import os
import json
import logging
import urllib.request
import jwt
from jwt.algorithms import RSAAlgorithm

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Read required environment variables
USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
APP_CLIENT_ID = os.environ['COGNITO_APP_CLIENT_ID']
REGION = os.environ['COGNITO_REGION']
# Using CONNECTIONS_TABLE since our code expects that key
DDB_TABLE = os.environ['CONNECTIONS_TABLE']

# Assume conn_table is a boto3 DynamoDB Table resource
import boto3

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
conn_table = dynamodb.Table(DDB_TABLE)

_jwks_cache = None


def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    token = None
    # First, try to get token from the Authorization header
    if event.get('headers') and event['headers'].get('Authorization'):
        auth_header = event['headers']['Authorization']
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
        else:
            token = auth_header

    # Then try queryStringParameters
    if not token and event.get('queryStringParameters'):
        token = event['queryStringParameters'].get('token')

    # Finally, if still no token, try to parse rawQueryString
    if not token and event.get('rawQueryString'):
        # Simple parsing: assumes query string format: "token=XYZ&..."
        params = dict(param.split('=') for param in event['rawQueryString'].split('&') if '=' in param)
        token = params.get('token')

    if not token:
        logger.warning("No JWT token found in connect request")
        raise Exception("Unauthorized")

    try:
        global _jwks_cache
        if not _jwks_cache:
            jwks_url = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
            with urllib.request.urlopen(jwks_url) as response:
                _jwks_cache = json.loads(response.read())['keys']
        headers = jwt.get_unverified_header(token)
        key_matches = [k for k in _jwks_cache if k["kid"] == headers.get("kid")]
        if not key_matches:
            logger.error("No matching key found for token")
            raise Exception("Unauthorized")
        public_key = RSAAlgorithm.from_jwk(json.dumps(key_matches[0]))
        claims = jwt.decode(token, public_key, algorithms=['RS256'], audience=APP_CLIENT_ID)
        principal_id = claims.get('sub')
    except Exception as e:
        logger.error("JWT validation failed: %s", e)
        raise Exception("Unauthorized")

    # Attempt to store connection info in DynamoDB
    try:
        connection_id = event.get("requestContext", {}).get("connectionId")
        conn_table.put_item(Item={"UserId": principal_id, "ConnectionId": connection_id})
    except Exception as e:
        logger.error("Failed to store connection: %s", e)
        raise Exception("Unauthorized")

    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": "Allow",
                "Resource": event.get("methodArn", "*")
            }]
        },
        "context": {
            "username": claims.get('cognito:username', principal_id)
        }
    }
    return policy