import boto3
from botocore.exceptions import ClientError


def create_parking_lots_table(dynamoDB=None):
    if not dynamoDB:
        dynamoDB = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")

    table = dynamoDB.Table("CloudCompParkingLotTask")
    try:
        is_table_existing = table.table_status in ("CREATING", "UPDATING",
                                                   "DELETING", "ACTIVE")
    except ClientError:
        is_table_existing = False
        return "Table %s doesn't exist." % table.name

    if not is_table_existing:
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
