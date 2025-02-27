import boto3
import botocore
import pytest
from moto import mock_aws

# Import the $connect Lambda's handler function from app/main.py
from app.main import lambda_handler

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Automatically set environment variables for tests."""
    # Set the TABLE_NAME environment variable as expected by the Lambda
    monkeypatch.setenv("TABLE_NAME", "ConnectionsTable")
    yield

@mock_aws
def test_connect_success(monkeypatch):
    """Test successful connection with valid authorization."""
    # **Arrange**: Create a DynamoDB table to simulate the environment
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    dynamodb.create_table(
        TableName="ConnectionsTable",
        KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST"
    )
    # Prepare a sample $connect event with valid authorization context
    event = {
        "requestContext": {
            "connectionId": "conn-id-123",
            "authorizer": {"principalId": "user123"}  # Simulate authorized user
        },
        "headers": {
            "Authorization": "Bearer valid-token"
        }
    }
    from types import SimpleNamespace
    context = SimpleNamespace(aws_request_id="test-request", function_name="$connect")
    # **Act**: Invoke the Lambda handler
    response = lambda_handler(event, context)
    # **Assert**: Check for 200 response and that the item is stored in DynamoDB
    assert response["statusCode"] == 200
    table = dynamodb.Table("ConnectionsTable")
    item = table.get_item(Key={"connectionId": "conn-id-123"}).get("Item")
    assert item is not None
    assert item.get("connectionId") == "conn-id-123"

@mock_aws
def test_connect_unauthorized():
    """Test that an unauthorized connection attempt returns 403 and stores no item."""
    # **Arrange**: Create the Connections table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    dynamodb.create_table(
        TableName="ConnectionsTable",
        KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST"
    )
    # Prepare an event missing authorization (no 'authorizer' field)
    event = {
        "requestContext": {
            "connectionId": "conn-id-unauth"
        },
        "headers": {}
    }
    from types import SimpleNamespace
    context = SimpleNamespace(aws_request_id="test-request", function_name="$connect")
    # **Act**: Invoke the Lambda handler
    response = lambda_handler(event, context)
    # **Assert**: Expect a 403 Unauthorized response and no item stored in DynamoDB
    assert response["statusCode"] == 403
    table = dynamodb.Table("ConnectionsTable")
    item = table.get_item(Key={"connectionId": "conn-id-unauth"}).get("Item")
    assert item is None

@mock_aws
def test_connect_dynamodb_error(monkeypatch, caplog):
    """Test handling of DynamoDB errors during connection (e.g., put_item failure)."""
    # Monkeypatch boto3.resource to simulate a DynamoDB exception on put_item
    class DummyTable:
        def put_item(self, Item):
            raise botocore.exceptions.ClientError({"Error": {"Code": "InternalError"}}, "PutItem")
    class DummyDynamoResource:
        def Table(self, name):
            return DummyTable()
    monkeypatch.setattr(boto3, "resource", lambda service, **kwargs: DummyDynamoResource() if service == "dynamodb" else boto3.resource(service, **kwargs))
    event = {
        "requestContext": {
            "connectionId": "conn-error",
            "authorizer": {"principalId": "user123"}
        },
        "headers": {
            "Authorization": "Bearer valid-token"
        }
    }
    from types import SimpleNamespace
    context = SimpleNamespace(aws_request_id="test-request", function_name="$connect")
    caplog.set_level("ERROR")
    response = lambda_handler(event, context)
    # **Assert**: Returns 500 when DynamoDB fails and logs an error
    assert response["statusCode"] == 500
    error_logs = [rec for rec in caplog.records if rec.levelname == "ERROR"]
    assert error_logs, "Expected an error log when DynamoDB fails"