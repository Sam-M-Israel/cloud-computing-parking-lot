import boto3
import json


class DynamoDB:

    def __init__(self):
        self.session = boto3.Session(profile_name='default')
        self.credentials = self.session.get_credentials()
        self.region = 'us-east-2'
        self.dynamo_client = self.create_client('dynamodb')
        self.sts_client = self.create_client('sts')
        self.iam_client = self.create_client('iam')
        self.account_id = self.sts_client.get_caller_identity()["Account"]
        self.table = self.create_dyno_table()

    def create_client(self, role_name='dynamodb'):
        return boto3.client(f'{role_name}', region_name=self.region,
                            aws_access_key_id=self.credentials.access_key,
                            aws_secret_access_key=self.credentials.secret_key)

    def create_policy(self):
        policy_name = "Cloud-Comp-Parking-Lot-Task-Policy"

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "ReadWriteTable",
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:BatchGetItem",
                        "dynamodb:GetItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:BatchWriteItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem"
                    ],
                    "Resource": f"arn:aws:dynamodb:{self.region}:"
                                f"{self.account_id}:table/{self.table.table_name}"
                },
                {
                    "Sid": "DynamoDBPolicy",
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:*"
                    ],
                    "Resource": "*"
                }
            ]
        }

        response = self.iam_client.create_policy(PolicyName=policy_name, PolicyDocument=json.dumps(policy))

        return response['Policy']['Arn']

    def create_dyno_table(self):

        table_name = "CloudCompParkingLotTask"
        existing_tables = self.dynamo_client.list_tables()['TableNames']

        if table_name not in existing_tables:
            dynamo_db = boto3.client('dynamodb', region_name=self.region)
            table = dynamo_db.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'ticket_id',
                        'KeyType': 'HASH'  # Partition key
                    },
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'ticket_id',
                        'AttributeType': 'S'
                    },
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                })
            return table
        else:
            try:
                response = self.dynamo_client.describe_table(TableName='test')
                return response
            except self.dynamo_client.exceptions.ResourceNotFoundException:
                # do something here as you require
                pass
