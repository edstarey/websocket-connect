import os
import json
import logging
import urllib.request
import urllib.parse
import jwt
from jwt.algorithms import RSAAlgorithm
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Read required environment variables
USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
APP_CLIENT_ID = os.environ['COGNITO_APP_CLIENT_ID']
REGION = os.environ['COGNITO_REGION']
DDB_TABLE = os.environ['CONNECTIONS_TABLE']

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
conn_table = dynamodb.Table(DDB_TABLE)

_jwks_cache = None

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))
    token = None

    # 1. Try to get token from the Authorization header.
    if event.get('headers'):
        auth_header = event['headers'].get('Authorization')
        logger.info("Authorization header: %s", auth_header)
        if auth_header:
            if auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1]
            else:
                token = auth_header

    # 2. Try to get token from queryStringParameters.
    if not token and event.get('queryStringParameters'):
        token = event['queryStringParameters'].get('token')

    # 3. Fallback: parse rawQueryString robustly using urllib.parse.
    if not token and event.get('rawQueryString'):
        raw_qs = event['rawQueryString']
        logger.info("rawQueryString: %s", raw_qs)
        parsed_qs = urllib.parse.parse_qs(raw_qs)
        token_list = parsed_qs.get('token')
        if token_list:
            token = token_list[0]

    if not token:
        logger.warning("No JWT token found in connect request")
        raise Exception("Unauthorized")

    # Validate the JWT token
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

    # Store the connection information in DynamoDB.
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
    logger.info("Authorization successful for principal: %s", principal_id)
    return policy