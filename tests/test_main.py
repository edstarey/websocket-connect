# tests/test_connect.py
import os
import boto3
import pytest
from moto import mock_aws

from app.main import lambda_handler


@pytest.fixture
def dynamodb_table():
    """Create a mock DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="ConnectionsTable",
            KeySchema=[{"AttributeName": "connection_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "connection_id", "AttributeType": "S"}],
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
            "connection_id": "conn-123",
            "authorizer": {"principalId": "user-abc"}
        }
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
    # Check the item in the table
    item = dynamodb_table.get_item(Key={"connection_id": "conn-123"}).get("Item")
    assert item is not None
    assert item["userId"] == "user-abc"

def test_connect_unauthorized(dynamodb_table):
    event = {
        "requestContext": {
            "connection_id": "conn-456"
            # No authorizer
        }
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 403
    # Should not store the connection
    item = dynamodb_table.get_item(Key={"connection_id": "conn-456"}).get("Item")
    assert item is None
