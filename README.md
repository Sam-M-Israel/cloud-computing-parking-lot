# cloud-computing-parking-lot

Cloud computing task for IDC CS Elective 3031

___Task::___
- Build a parking lot app which can be automatically deployed to either AWS lambda or EC2 - this is the EC2
- The app should be able to handle 2 entry points:
    1. /entry?plate=XXX-XXX-XXXX&parkingLot=XXX    and returns ticket id
    2. /exit?ticketID=XXXXXXX (for however you define the ticketID to be)    and returns the license plate, total parked time, the parking lot id and the charge (based
on 15 minutes increments [Cost is $10 an hour -> $2.5 per 15 minutes]).
    
       
___File Structure:___
```
Ex01
└── app.py
└── init_dynamoDB.py
└── requirements.txt
└── setup.sh
└── launch_script.sh
└── trust-policy.json
└── create-table.json

The files app.py, init_dynamoDB.py, and requirements.txt are the actual app files.

```

___Files used for automatic deploy/setup of the EC2 & server:___
- setup.sh -> creation of the DynamoDB table, EC2 instance, permissions, and automatic deploy to newly created EC2 instance + installation of all required libraries on the EC2
- launch_script.sh -> script run by the setup.sh on the EC2. Installs all the required libraries and tools needed, setups AWS permissions and the like. Pulls the flask server code from github, sets it up and starts the server
- trust-policy.json -> initial trust policy created for the iam role
- create-table.json -> DynamoDB table definition

___Files used strictly for the flask app setup & running:___
- app.py -> the flask server - handles all the required actions'
- init_dynamoDB.py -> gets/uses all the required permissions. Creates the dynamo db table if there was an error, and it wasn't created in the setup.sh script
- requirements.txt -> the requirements file for the flask app. 
