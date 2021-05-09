import os
import socket
import appscript
import platform
import boto3
import time
import requests
import subprocess

from botocore.exceptions import ClientError

ec2 = boto3.resource('ec2', region_name='us-east-2')
ec2_client = boto3.client('ec2', region_name='us-east-2')
# Current time in milliseconds
run_id = int(round(time.time() * 1000))


def create_key_pair(instance_name='ec2'):
    key_name = f'{instance_name}-{run_id}'
    key_pem = f'{key_name}.pem'
    print(f'Creating key pair {key_name} to connect to instances and save locally')
    # create a file to store the key locally
    outfile = open(key_pem, 'w')

    # call the boto ec2 function to create a key pair
    key_pair = ec2.create_key_pair(KeyName=key_name)

    # capture the key and store it in a file
    key_pair_out = str(key_pair.key_material)
    outfile.write(key_pair_out)
    outfile.close()
    # Securing the key pair
    subprocess.call(['chmod', '400', key_pem])
    print(f'Key pair created and secured')
    return key_name


def create_security_group():
    security_group_name = f'my-sg-parking-lot-task-{run_id}'
    print(f'Setting up firewall for {security_group_name}')
    response = ec2_client.describe_vpcs()
    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
    try:
        response = ec2_client.create_security_group(GroupName=f'{security_group_name}',
                                             Description='Access to my instances', VpcId=vpc_id)
        security_group_id = response['GroupId']
        print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))
        r = requests.get(r'http://jsonip.com')
        my_ip = r.json()['ip']
        print(f'My IP: {my_ip}')
        data = ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                 'FromPort': 5000,
                 'ToPort': 5000,
                 'IpRanges': [{'CidrIp': f'{my_ip}/32'}]},
                {'IpProtocol': 'tcp',
                 'FromPort': 22,
                 'ToPort': 22,
                 'IpRanges': [{'CidrIp': f'{my_ip}/32'}]}
            ])
        print('Ingress Successfully Set %s' % data)
        return security_group_id
    except ClientError as e:
        print(e)


def create_ec2_instance(key_pair_name,security_group_id):
    print('Creating a new ec2 instance')
    # create a new EC2 instance
    script_file = open("launch_script.sh").read()
    instances = ec2.create_instances(
        ImageId='ami-08962a4068733a2b6',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName=key_pair_name,
        UserData=script_file,
        SecurityGroupIds=[security_group_id]
    )

    print('Getting instance with out key pair')
    response = ec2_client.describe_instances(Filters=[{'Name': 'key-name', 'Values': [key_pair_name]}])
    reservations = response['Reservations']
    instances = reservations[0]['Instances']

    if len(instances) == 0:
        print(f'Error creating instance instance with key-pair: {key_pair_name}')
        return False
    else:
        instance = instances[0]
        while instance['State']['Name'] != 'running':
            print(f'...instance is in {instance["State"]} state')
            time.sleep(10)
            response = ec2_client.describe_instances(
                Filters=[{'Name': 'key-name', 'Values': [key_pair_name]}])
            reservations = response['Reservations']
            instances = reservations[0]['Instances']
            instance = instances[0]

        print(f'Public IP address is: {instance["PublicIpAddress"]}')
        print(f'New instance {instance["InstanceId"]} @ {instance["PublicIpAddress"]}')
        return instance


def connect_to_ec2_and_deploy(ec2_instance, key_pair, public_ip):
    current_platform = platform.system()
    result = {
        'Linux': 'gnome-terminal',
        'Darwin': 'Terminal.app',
        'Windows': 'cmd.exe'
    }
    command_line = result[current_platform]

    # bash_command = f'ssh -i {key_pair} -o \"StrictHostKeyChecking=no\" -o ' \
    #                f'\"ConnectionAttempts=10\" ubuntu@{public_ip} <<EOF sudo apt -f ' \
    #                'install\nsudo apt -y update && sudo apt -y dist-upgrade sudo apt ' \
    #                'install git\nsudo apt -y install python3-pip\nsudo apt install ' \
    #                'build-essential libssl-dev libffi-dev python3-dev\nsudo apt ' \
    #                'install -y python3-venv\ngit clone ' \
    #                'https://github.com/Sam-M-Israel/cloud-computing-parking-lot.git' \
    #                '\ncd cloud-computing-parking-lot\npip3 install -r ' \
    #                'requirements.txt && pip3 freeze > requirements.txt\nexport ' \
    #                'FLASK_APP=app.py && export FLASK_ENV=development && export ' \
    #                'FLASK_DEBUG=0\nnohup flask run --host 0.0.0.0  &>/dev/null ' \
    #                '&\nexit\nEOF'

    # public_ip = f'ec2-{public_ip.replace(".", "-")}'
    # bash_command = f'ssh -i "{key_pair}.pem" ' \
    #                f'ubuntu@{public_ip}.us-east-2.compute.amazonaws.com'

    file_upload_command = f'scp -i "{key_pair}.pem" -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" launch_script.sh ubuntu@{public_ip}:/home/ubuntu/'
    bash_command = f'ssh -i "{key_pair}.pem" -o "StrictHostKeyChecking=no" -o ' \
                   f'"ConnectionAttempts=10" ubuntu@{public_ip}'

    working_directory = os.path.abspath(os.getcwd())
    if current_platform == 'Windows':
        os.system(
            f"start /B start cmd.exe @cmd /k cd {working_directory} && {file_upload_command} && {bash_command}")
    elif current_platform == 'Darwin':
        appscript.app('Terminal').do_script(f'cd {working_directory} && {file_upload_command} && {bash_command}')
    else:
        os.system(f'gnome-terminal -- cd {working_directory} && {file_upload_command} && {bash_command}')




def deploy():
    key_pair_name = create_key_pair('parking-lot-task')
    security_group_id = create_security_group()
    ec2_machine = create_ec2_instance(key_pair_name, security_group_id)
    public_ip = ec2_machine["PublicIpAddress"]
    connect_to_ec2_and_deploy(ec2_machine, key_pair_name, public_ip)
    print('Sammy')


if __name__ == '__main__':
    deploy()

