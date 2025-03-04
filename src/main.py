import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_table():
    return boto3.resource("dynamodb", region_name="us-east-1").Table(os.environ["TABLE_NAME"])

def lambda_handler(event, context):
    """
    Handle new WebSocket connection: store connection ID along with tenant info.
    Expects tenant info to be provided in the query string parameters.
    """
    connectionId = event["requestContext"]["connectionId"]

    # Retrieve the authorizer context.
    authorizer_context = event["requestContext"].get("authorizer")
    if not authorizer_context:
        logger.error("Unauthorized: no authorizer provided.")
        return {"statusCode": 403, "body": "Unauthorized"}

    # Extract userId from the authorizer.
    user_id = authorizer_context.get("principalId")

    # Extract tenant info from the query parameters (or headers) sent by the frontend.
    tenant_id = event.get("queryStringParameters", {}).get("tenantId")
    if not tenant_id:
        logger.error("Tenant information is missing in the connection request.")
        return {"statusCode": 400, "body": "Tenant information is required."}

    # Build the item to store.
    item = {
        "connectionId": connectionId,
        "tenant_id": tenant_id
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
