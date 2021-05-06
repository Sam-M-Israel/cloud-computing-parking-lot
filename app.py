import datetime
import simplejson as json
from flask import Flask, request, jsonify, abort
import boto3
import time
import ParkingLotCreateTable
import decimal
import math


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return int(obj)
    raise TypeError


app = Flask(__name__)

__TableName__ = "CloudCompParkingLotTask"

Primary_Column_Name = "ticket_id"
Default_Primary_Key = 1
session = boto3.Session(profile_name='default')
credentials = session.get_credentials()
AWS_ACCESS_KEY = credentials.access_key

dynamoDB = boto3.client('dynamodb', region_name='us-east-2',
                        aws_access_key_id=credentials.access_key,
                        aws_secret_access_key=credentials.secret_key)
ParkingLotCreateTable.create_parking_lots_table(dynamoDB)
table = dynamoDB.Table(__TableName__)


def get_car_by_ticket_id(ticket_id):
    res = table.get_item(Key={Primary_Column_Name: ticket_id})
    if 'Item' not in res:
        return {"nonexist": "car doesn't exist in db"}

    return res['Item']


def create_new_ticket_id(current_time, plate_number, parking_lot):
    return str(current_time) + str(parking_lot) + str(plate_number[-4:])


# hourly rate for parking is $10 -> each 15 minute interval is $2.5 -> we are
# charging for every 15 min interval that has been started
def get_payment_amount(entry_time):
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
        result.parking_lot_num = f'\n {err_str}' if len(result["plate_num"]) > 0 else f'{standard_error}{err_str}'

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
        check_exists = get_car_by_ticket_id(ticket_id)

        if not check_exists["nonexist"]:
            return "Vehicle already exists in garage"

        new_car = {
            Primary_Column_Name: ticket_id,
            "parking_lot": parking_lot_number,
            "plate_number": plate_number,
            "entry_time": current_time,
        }
        res = table.put_item(Item=new_car)


        car = get_car_by_ticket_id(ticket_id)
    return json.dumps(car, indent=2, default=decimal_default)


@app.route("/exit")
def vehicle_exit():
    ticket_id = request.args.get('ticketId')
    check_validity = check_exit_query_params_validity(ticket_id)

    if not check_validity["isValid"]:
        return jsonify({"error": check_validity["ticket_id"]})

    exiting_vehicle = None
    try:
        exit_res = table.get_item(Key={"ticket_id": ticket_id})
        delete_res = table.delete_item(Key={"ticket_id": ticket_id})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        if 'Item' in exit_res.keys():
            exiting_vehicle = dict(exit_res['Item'])
            parked_duration, amount_to_pay = get_payment_amount(exiting_vehicle["entry_time"])
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
