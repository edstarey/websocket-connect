import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_table():
    return boto3.resource("dynamodb", region_name="us-east-1").Table(os.environ["TABLE_NAME"])

def lambda_handler(event, context):
    """
    Handle new WebSocket connection: store connection ID (and tenant info) in DynamoDB.
    Requires a valid authorizer context to proceed.
    """
    connectionId = event["requestContext"]["connectionId"]

    # Retrieve the authorizer context.
    authorizer_context = event["requestContext"].get("authorizer")
    if not authorizer_context:
        logger.error("Unauthorized: no authorizer provided.")
        return {"statusCode": 403, "body": "Unauthorized"}

    # Extract both userId and tenant_id if available.
    user_id = authorizer_context.get("principalId")
    # You may have tenant information provided either separately or as part of the user's claims.
    tenant_id = authorizer_context.get("tenant_id") or user_id

    # Build the item to store; include tenant_id.
    item = {
        "connectionId": connectionId,
        "tenant_id": tenant_id  # explicitly store tenant_id for later queries
    }
    if user_id:
        item["userId"] = user_id

    table = get_table()
    try:
        table.put_item(Item=item)
        logger.info(f"Connected: stored connection {connectionId} for tenant {tenant_id} (user: {user_id})")
    except Exception as e:
        logger.error(f"Error storing connectionId {connectionId} in DynamoDB: {e}")
        return {"statusCode": 500, "body": "Failed to connect."}

    return {"statusCode": 200, "body": "Connected."}