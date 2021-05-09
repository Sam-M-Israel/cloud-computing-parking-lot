from time import sleep
import boto3
import json
import pandas as pd


class DynamoDB:

    def __init__(self):
        self.session = boto3.Session(profile_name='default')
        self.credentials = self.session.get_credentials()
        self.region = 'us-east-2'
        self.dynamo_client = self.create_client('dynamoDB')
        self.sts_client = self.create_client('sts')
        self.iam_client = self.create_client('iam')
        self.account_id = self.sts_client.get_caller_identity()["Account"]
        self.table = self.create_table()

    def create_client(self, role_name='dynamoDB'):
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

    def create_table(self):
        dynamo_db = boto3.resource('dynamodb', region_name=self.region)
        with open('create-table.json') as fp:
            data = json.load(fp)

        return dynamo_db.create_table(data)

