# debug
# set -o xtrace

REGION=$(aws ec2 describe-availability-zones | jq -r .AvailabilityZones[0].RegionName)
AWS_ACCOUNT=$(aws sts get-caller-identity  | jq -r .Account)
RUN_ID=$(date +'%sN')
KEY_NAME="parking-lot-task-$RUN_ID"
KEY_PEM="$KEY_NAME.pem"
AWS_ROLE="ec2-to-dynoDB-role-$RUN_ID"

echo "Creating role $AWS_ROLE..."
aws iam create-role --role-name $AWS_ROLE --assume-role-policy-document file://trust-policy.json

echo "Allowing access to DynamoDB..."
aws iam attach-role-policy --role-name $AWS_ROLE  \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

echo "Waiting for role creation..."
aws iam wait role-exists --role-name $AWS_ROLE
aws iam get-role --role-name $AWS_ROLE
ARN_ROLE=$(aws iam get-role --role-name $AWS_ROLE | jq -r .Role.Arn)

echo "Workaround consistency rules in AWS roles after creation... (sleep 10)"
sleep 10

aws dynamodb create-table --cli-input-json file://create-table.json
echo "Got to hereeee"

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

echo "Creating Ubuntu 20.04 instance..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t2.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP)

INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID |
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $PUBLIC_IP"
echo "deploying code to production"
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" launch_script.sh ubuntu@$PUBLIC_IP:/home/ubuntu/

echo "setup production environment"
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP <<EOF
  sh -e launch_script.sh
EOF

echo "test that it all worked"
curl  --retry-connrefused --retry 10 --retry-delay 1  http://$PUBLIC_IP:5000


