#!/bin/sh
echo "Starting setup..."
sudo apt -f install
sudo apt -y update && sudo apt -y dist-upgrade
sudo apt install git
sudo apt -y install python3-pip
echo "Installing AWS CLI..."
pip3 install --upgrade awscli
sudo apt install awscli zip
echo "AWS CLI installed, please enter your credentials"
aws configure
sudo apt -y install build-essential libssl-dev libffi-dev python3-dev
sudo apt install -y python3-venv
git clone https://github.com/Sam-M-Israel/cloud-computing-parking-lot.git
echo "Successfully cloned github code..."
cd cloud-computing-parking-lot
pip3 install -r requirements.txt && pip3 freeze > requirements.txt
export FLASK_APP=app.py && export FLASK_ENV=production && export FLASK_DEBUG=0
echo "Starting flask server, you can access this instances EC2 public IP, port 5000"
nohup flask run --host 0.0.0.0 >/dev/null & exit
