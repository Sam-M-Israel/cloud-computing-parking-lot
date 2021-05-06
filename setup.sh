# debug
# set -o xtrace

RUN_ID=$(date +'%sN')
KEY_NAME="parking-lot-task-$RUN_ID"
KEY_PEM="$KEY_NAME.pem"
AWS_ROLE="ec2-to-dynoDB-role-$RUN_ID"

#aws iam wait role-exists --role-name $AWS_ROLE
#aws iam get-role --role-name $AWS_ROLE
#ARN_ROLE=$(aws iam get-role --role-name $AWS_ROLE | jq -r .Role.Arn)
#
#echo "Workaround consistency rules in AWS roles after creation... (sleep 10)"
#sleep 10
#
#echo "Allowing access to DynamoDB..."
#aws iam attach-role-policy --role-name $AWS_ROLE  \
#    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
#
#aws dynamodb create-table --cli-input-json file://create-table.json

echo "create key pair $KEY_PEM to connect to instances and save locally"
aws ec2 create-key-pair --key-name $KEY_NAME \
    | jq -r ".KeyMaterial" > $KEY_PEM

# secure the key pair
chmod 400 $KEY_PEM

# shellcheck disable=SC2006
SEC_GRP="my-sg-parking-lot-task-$RUN_ID"

echo "setup firewall $SEC_GRP"
aws ec2 create-security-group   \
    --group-name $SEC_GRP       \
    --description "Access my instances"

# figure out my ip
MY_IP=$(curl ipinfo.io/ip)
echo "My IP: $MY_IP"


echo "setup rule allowing SSH access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 22 --protocol tcp \
    --cidr $MY_IP/32

echo "setup rule allowing HTTP (port 5000) access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 5000 --protocol tcp \
    --cidr $MY_IP/32

UBUNTU_20_04_AMI="ami-08962a4068733a2b6"

#echo "Creating Ubuntu 20.04 instance..."
#RUN_INSTANCES=$(aws ec2 run-instances   \
#    --image-id $UBUNTU_20_04_AMI        \
#    --instance-type t2.micro            \
#    --key-name $KEY_NAME                \
#    --security-groups $SEC_GRP)
#
#INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids i-0fe4e8140ec753811

PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids i-0fe4e8140ec753811 |
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $PUBLIC_IP"

echo "setup production environment"
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP <<EOF
    sudo apt -f install
    sudo apt -y update && sudo apt -y dist-upgrade
    sudo apt install git
    sudo apt -y install python3-pip
    sudo apt install build-essential libssl-dev libffi-dev python3-dev
    sudo apt install -y python3-venv
    git clone https://github.com/Sam-M-Israel/cloud-computing-parking-lot.git
    cd cloud-computing-parking-lot
    python3 -m venv cloud-computing-parking-lot
    source cloud-computing-parking-lot/bin/activate
    pip3 install -r requirements.txt && pip3 freeze > requirements.txt
    export FLASK_APP=app.py && export FLASK_ENV=development && export FLASK_DEBUG=0
    nohup flask run --host 0.0.0.0  &>/dev/null &
    exit
EOF

#echo "deploying code to production"
#scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" app.py ubuntu@$PUBLIC_IP:/home/ubuntu/
#

echo "test that it all worked"
curl  --retry-connrefused --retry 10 --retry-delay 1  http://$PUBLIC_IP:5000


