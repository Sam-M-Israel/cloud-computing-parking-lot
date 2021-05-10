import datetime
import simplejson as json
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from flask import Flask, request, jsonify
import time
import decimal
import math
from .init_dynamoDB import DynamoDB as dyno

app = Flask(__name__)
dyno_instance = dyno()
table = dyno_instance.create_dyno_table()
client = dyno_instance.dynamo_client
resource = dyno_instance.dynamo_resource
__TableName__ = "CloudCompParkingLotTask"


def error_messages(main_err, secondary_message=None):
    message = f'Error: {main_err}.'
    if secondary_message is not None:
        message += f' {secondary_message}'
    return {"error": message}


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return int(obj)
    raise TypeError


def get_car_by_ticket_id(ticket_id):
    res = client.get_item(TableName=__TableName__, Key={"ticket_id": ticket_id})
    if 'Item' not in res:
        return error_messages('vehicle doesn\'t exist in garage', 'Please enter the '
                                                                  'proper ticket ID.')

    return res['Item']


def get_car_by_license_plate(license_plate):
    """
    TODO: Need to implement this. Change the table to also ALSO be able to sort by
    the license plate number
    :param license_plate:
    :return:
    """
    res = client.query(TableName=__TableName__,KeyConditionExpression=Key('plate').eq(license_plate))
    if 'Item' not in res:
        return error_messages('vehicle doesn\'t exist in garage',
                              'Please enter the correct license plate number.')
    return res['Item']


def create_new_ticket_id(current_time, plate_number, parking_lot):
    return str(current_time) + str(parking_lot) + str(plate_number[-4:])


def get_payment_amount(entry_time):
    """
    hourly rate for parking is $10 -> each 15 minute interval is $2.5 -> we are
    charging for every 15 min interval that has been started
    :param entry_time:
    :return:
    """
    current_time = int(round(time.time() * 1000))
    exit_time = datetime.datetime.fromtimestamp(current_time / 1e3)
    entry_time = datetime.datetime.fromtimestamp(float(entry_time) / 1e3)
    duration = exit_time - entry_time
    minutes_passed = divmod(duration.total_seconds(), 60)[0]
    rounded_intervals = int(math.floor(minutes_passed / 15))
    num_charging_periods = rounded_intervals if minutes_passed % 15 == 0 else rounded_intervals + 1
    return duration, num_charging_periods * 2.5


def check_entry_query_params_validity(plate_num, parking_lot_num):
    result = {
        "plate_num": '',
        "parking_lot_num": ''
    }
    standard_error = 'Entry params error.\n'
    if not plate_num or len(plate_num) == 0:
        result["plate_num"] = f'{standard_error}No plate number was given.'
    if len(plate_num) < 11 or len(plate_num) > 11:
        result["plate_num"] = f'{standard_error}Invalid number of characters in the ' \
                              f'plate number. '
    if not parking_lot_num or len(parking_lot_num) == 0:
        err_str = 'No parking lot number was given.'
        result.parking_lot_num = f'\n {err_str}' if len(
            result["plate_num"]) > 0 else f'{standard_error}{err_str}'

    result["plate_num"] = True if len(result["plate_num"]) == 0 else result["plate_num"]
    result["parking_lot_num"] = True if len(
        result["parking_lot_num"]) == 0 else result["parking_lot_num"]

    return result


def check_exit_query_params_validity(ticket_id):
    result = {
        "ticket_id": '',
        "isValid": True,
    }
    standard_error = 'Exit params error.\n'
    if not ticket_id or len(ticket_id) == 0:
        result["isValid"] = False
        result["ticket_id"] = f'{standard_error} Please provide your ticket id'
    if len(ticket_id) < 18:
        result["isValid"] = False
        result["ticket_id"] = f'{standard_error} Please provide a valid ticket id'

    return result


@app.route("/entry")
def vehicle_entry():
    plate_number = request.args.get('plate')
    parking_lot_number = request.args.get('parkingLot')
    if not plate_number or not parking_lot_number:
        return "Error, missing param/s"

    validity_check = check_entry_query_params_validity(plate_number, parking_lot_number)
    error = False
    if validity_check["plate_num"] is not True:
        error = validity_check["plate_num"]

    if validity_check["parking_lot_num"] is not True:
        error += str('\n' + validity_check["parking_lot_num"])
    if error is True:
        return jsonify({"error": error})
    else:
        current_time = round(time.time() * 1000)
        ticket_id = create_new_ticket_id(current_time, plate_number, parking_lot_number)
        check_exists = get_car_by_license_plate(plate_number)

        if not check_exists["error"]:
            return "Vehicle already exists in garage"

        new_car = {
            "ticket_id": {'S': ticket_id},
            "parking_lot": {'N': str(parking_lot_number)},
            "plate_number": {'S': plate_number},
            "entry_time": {'N': str(current_time)},
        }

        res = client.put_item(TableName=__TableName__, Item=new_car)
        newTable = resource.Table(__TableName__)
        response = newTable.scan()
        data = response['Items']
        print("Printing the table")
        print(data)
        if res["ResponseMetadata"]["HTTPStatusCode"] != 200:
            entry_string = f'Garage is full'
        else:
            entry_string = f'Your ticket ID is: {ticket_id}'
        return entry_string


@app.route("/exit")
def vehicle_exit():
    ticket_id = request.args.get('ticketId')
    check_validity = check_exit_query_params_validity(ticket_id)

    if not check_validity["isValid"]:
        return jsonify({"error": check_validity["ticket_id"]})

    exiting_vehicle = None
    try:
        exit_res = client.get_item(TableName=__TableName__,
                                   Key={"ticket_id": ticket_id})
        delete_res = client.delete_item(TableName=__TableName__,
                                        Key={"ticket_id": ticket_id})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        if 'Item' in exit_res.keys():
            exiting_vehicle = dict(exit_res['Item'])
            parked_duration, amount_to_pay = get_payment_amount(
                exiting_vehicle["entry_time"])
            exiting_vehicle.update({"total_parked_time": str(parked_duration)})
            exiting_vehicle.update({"charge": float(amount_to_pay)})
        else:
            exiting_vehicle = "Vehicle doesn't exist in parking lots"
    return json.dumps(exiting_vehicle), 201


@app.route("/")
def home():
    return "Hello World!"


if __name__ == '__main__':
    app.run(debug=True)
