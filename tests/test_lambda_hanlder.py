import os
import boto3
import pytest
from moto import mock_dynamodb

from src.lambda_handler import lambda_handler

@pytest.fixture
def dynamodb_table():
    """Create a mock DynamoDB table."""
    with mock_dynamodb():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="ConnectionsTable",
            KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        table.wait_until_exists()
        yield table

@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    """Set environment variables for the Lambda."""
    monkeypatch.setenv("TABLE_NAME", "ConnectionsTable")
    yield

def test_connect_authorized(dynamodb_table):
    event = {
        "requestContext": {
            "connectionId": "conn-123",
            "authorizer": {"principalId": "user-abc"}
        },
        "queryStringParameters": {"tenantId": "tenant-xyz"}  # Added tenant information
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
    # Check the item in the table.
    item = dynamodb_table.get_item(Key={"connectionId": "conn-123"}).get("Item")
    assert item is not None
    assert item["userId"] == "user-abc"
    assert item["tenant_id"] == "tenant-xyz"

def test_connect_unauthorized(dynamodb_table):
    event = {
        "requestContext": {
            "connectionId": "conn-456"
            # No authorizer provided.
        }
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 403
    # Verify that the connection was not stored.
    item = dynamodb_table.get_item(Key={"connectionId": "conn-456"}).get("Item")
    assert item is None