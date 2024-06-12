import os

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

@app.task(name='task.tokenizer')
def token():
    return 'github-pat-token'

@app.task(name='tasks.nomad')
def nomad(job_name):
    # We don't restart the container when nomad updates the env variable
    # that corresponds to our token (for renewals). So grab it every
    # time we want to use it. Technically there is a race condition
    # a retry x3 loop or some such should probably resolve
    acl_token = os.environ["NOMAD_TOKEN"]
    # The job doesn't take parameters but the api gets mad at an empty body
    # hence the Meta field with nothing in it
    r = requests.post(f'http://nomad.service.consul:4646/v1/job/{job_name}/dispatch', json={'Meta': {}}, headers={"X-Nomad-Token": acl_token})
