import json
import boto3
import zipfile
import os

import botocore

# Define variables
function_name = 'parking-lot-lambda'
iam_role_name = 'lambda-execution-role'
zip_file_name = 'parking-lot-dep.zip'
handler_name = 'app.lambda_handler'
timeout = 30
memory_size = 128

# Define paths
current_directory = os.getcwd()
session = boto3.Session()

# Create IAM role
iam = session.client('iam')
assume_role_policy_document = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Effect': 'Allow',
            'Principal': {
                'Service': 'lambda.amazonaws.com'
            },
            'Action': 'sts:AssumeRole'
        }
    ]
}
try:
    role = iam.create_role(
        RoleName=iam_role_name,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy_document)
    )
except iam.exceptions.EntityAlreadyExistsException:
    role = iam.get_role(RoleName=iam_role_name)

iam.attach_role_policy(
    RoleName=iam_role_name,
    PolicyArn='arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess'
)

iam.attach_role_policy(
    RoleName=iam_role_name,
    PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
)

print(f"IAM role {iam_role_name} created successfully")

# Create Lambda function
file_path = os.path.join(current_directory, "app.py")
lambda_client = session.client('lambda')
zip_file = zipfile.ZipFile(f"{file_path}.zip", 'w', zipfile.ZIP_DEFLATED)
zip_file.write(file_path, os.path.relpath(file_path, current_directory), compress_type=zipfile.ZIP_DEFLATED)
zip_file.close()

with open(file_path, 'rb') as file:
    deployment_package = file.read()

try:
    function = lambda_client.create_function(
        FunctionName=function_name,
        Runtime='python3.9',
        Role=role['Role']['Arn'],
        Handler=handler_name,
        Code={
            'ZipFile': open(f"{file_path}.zip", 'rb').read()
        },
        Timeout=timeout,
        MemorySize=memory_size
    )
    print(f'Lambda function {function_name} created successfully')

except:
    function_data = lambda_client.get_function(FunctionName=function_name)
    if function_data:
        function = lambda_client.update_function_code(
            FunctionName=function_data['Configuration']['FunctionArn'],
            ZipFile=open(f"{file_path}.zip", 'rb').read()
        )

try:
    # Print out the API Gateway URL
    func = lambda_client.create_function_url_config(
        FunctionName=function_name,
        AuthType='NONE'
    )
    print(f"The lambda function URL: {func['FunctionUrl']}")

except:
    print(f'Lambda function {function_name} retrieved successfully')
    func = lambda_client.update_function_url_config(
        FunctionName=function_name,
        AuthType='NONE'
    )
    print(f"The lambda function URL: {func['FunctionUrl']}")

# Add permission for API Gateway to invoke the Lambda function
try:
    per = lambda_client.add_permission(
        FunctionName=function_name,
        StatementId='FunctionURLAllowPublicAccess',
        Action='lambda:InvokeFunctionUrl',
        Principal='*',
        FunctionUrlAuthType='NONE'
    )
except:
    print("Permission already exists")

dynamodb = session.client('dynamodb')
table_name = 'parking_tickets'
try:
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'ticket_id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'ticket_id',
                'AttributeType': 'S'
            }
        ],
        BillingMode='PROVISIONED',
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    print(f'Table {table_name} created successfully')

except:
    print("Table already exists")
    table = dynamodb.describe_table(TableName=table_name)

print("Deployment ended successfully!")

