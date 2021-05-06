import boto3
from botocore.exceptions import ClientError


def create_parking_lots_table(dynamoDB=None, credentials=None):
    if not dynamoDB:
        dynamoDB = boto3.client('dynamodb', endpoint_url="http://localhost:8000", aws_access_key_id=credentials.access_key,
                        aws_secret_access_key=credentials.secret_key)

        response = dynamoDB.describe_table(
            TableName='CloudCompParkingLotTask'
        )

        print("Creating table...")
        table = dynamoDB.create_table(
            TableName='CloudCompParkingLotTask',
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
            }
        )
        return table


if __name__ == '__main__':
    parking_table = create_parking_lots_table()
    print("Table status:", parking_table.table_status)
