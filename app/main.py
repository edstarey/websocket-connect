import os, boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])


def lambda_handler(event, context):
    connection_id = event["requestContext"]["connectionId"]
    # Get user identity from authorizer (if provided)
    auth_context = event["requestContext"].get("authorizer", {})
    user_id = auth_context.get("sub") or auth_context.get("principalId")

    item = {"connectionId": connection_id}
    if user_id:
        item["userId"] = user_id

    # Store connection in DynamoDB
    try:
        table.put_item(Item=item)
        print(f"Connected: stored connection {connection_id} for user {user_id}")
    except Exception as e:
        print("Error storing connection:", e)
        # Return error status if DynamoDB write fails
        return {"statusCode": 500, "body": "Failed to connect"}

    return {"statusCode": 200, "body": "Connected"}