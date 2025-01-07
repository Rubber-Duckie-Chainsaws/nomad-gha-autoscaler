import jwt
import os
import sys
import time

import boto3
import consul
import requests

from botocore.config import Config
from celery import Celery

USERNAME = os.environ["RABBIT_USER"]
PASSWORD = os.environ["RABBIT_PASS"]
CONNECTION_ADDRESS = os.environ["RABBIT_URL"]
VHOST = os.environ["RABBIT_VHOST"]

BROKER_URL = f'amqp://{USERNAME}:{PASSWORD}@{CONNECTION_ADDRESS}/{VHOST}'
BACKEND_URL = f'rpc://{USERNAME}:{PASSWORD}@{CONNECTION_ADDRESS}/{VHOST}'

app = Celery('node_requests', backend=BACKEND_URL, broker=BROKER_URL)

@app.task(name='tasks.ec2')
def ec2(class_name):
    my_config = Config(
        region_name = 'us-east-1'
    )
    ec2_client = boto3.client('ec2', config=my_config)
    asg_client = boto3.client('autoscaling', config=my_config)

    # Get launch template
    con = consul.Consul(host=os.environ["CONSUL_ADDR"])
    (_, class_info) = con.kv.get(f'services/{class_name}', recurse=True)
    autoscaling_name = None
    if class_info is None:
        raise KeyError("Key returned nothing from consul")
    else:
        for kv in class_info:
            if kv.get('Key', '') == f'services/{class_name}/autoscaling_group/name':
                autoscaling_name = kv.get('Value', None).decode('UTF-8')

    if autoscaling_name is None:
        raise KeyError('Autoscaling group name not present in consul')

    response = asg_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[
            autoscaling_name
        ]
    )

    capacity = response.get('AutoScalingGroups', [{}])[0].get('DesiredCapacity', None)
    if capacity is None:
        raise KeyError('Unknown Desired Capacity')


    response = asg_client.set_desired_capacity(
        AutoScalingGroupName=autoscaling_name,
        DesiredCapacity=capacity+1
    )

    return class_info

@app.task(name='tasks.tokenizer')
def token(org='rubber-duckie-chainsaws', name='new-auto-worker'):
    with open('/etc/pki', 'rb') as pem_file:
        signing_key = pem_file.read()

    CLIENT_ID = os.environ["GH_APP_CLIENT_ID"]
    INSTALLATION_ID = os.environ["GH_APP_INSTALL_ID"]
    payload = {
        'iat': int(time.time()),
        'exp': int(time.time()) + 120,
        'iss': CLIENT_ID,
    }

    # Create JWT
    encoded_jwt = jwt.encode(payload, signing_key, algorithm='RS256')

    access_token_headers = {
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f'Bearer {encoded_jwt}',
        "Accept": 'application/vnd.github+json'
    }
    access_request = requests.post(f'https://api.github.com/app/installations/{INSTALLATION_ID}/access_tokens', headers=access_token_headers)
    json_body = access_request.json()
    user_token = json_body.get('token', 'token-not-found')

    registration_token_headers = {
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f'Bearer {user_token}',
        "Accept": 'application/vnd.github+json'
    }
    token_request = requests.post(f'https://api.github.com/orgs/{org}/actions/runners/registration-token', headers=registration_token_headers)
    json_body = token_request.json()

    return_payload = {'token': json_body.get('token', 'token-not-found')}
    return return_payload

@app.task(name='tasks.longtest')
def long_test():
    time.sleep(15)
    return "Waited"

@app.task(name='tasks.nomad')
def nomad(meta_blob, job_name):
    # We don't restart the container when nomad updates the env variable
    # that corresponds to our token (for renewals). So grab it every
    # time we want to use it. Technically there is a race condition
    # a retry x3 loop or some such should probably resolve
    acl_token = os.environ["NOMAD_TOKEN"]
    # The job doesn't take parameters but the api gets mad at an empty body
    # hence the Meta field with nothing in it
    r = requests.post(f'http://nomad.service.consul:4646/v1/job/{job_name}/dispatch', json={'Meta': meta_blob, "namespace": "build"}, headers={"X-Nomad-Token": acl_token})
