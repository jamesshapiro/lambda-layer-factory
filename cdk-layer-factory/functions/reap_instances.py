import boto3
import datetime
import os
import json
import pytz

ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    my_region = os.environ['EC2_REGION']
    ec2_client = boto3.client('ec2', region_name=my_region)
    response = ec2_client.describe_instances()['Reservations']
    now = datetime.datetime.now().replace(tzinfo=None)
    kill_list = []
    for reservation in response:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            if instance['State']['Name'] == 'terminated':
                continue
            launch_time = instance['LaunchTime'].replace(tzinfo=None)
            delta = now - launch_time
            if delta.seconds < 900:
                continue
            if 'Tags' in instance:
                tags = instance['Tags']
                for tag in tags:
                    if tag['Key'] == 'APPLICATION' and tag['Value'] == 'CDK_LAMBDA_LAYER_FACTORY':
                        kill_list.append(instance_id)
    print(f'killing: {kill_list}')
    ec2_client.terminate_instances(InstanceIds=kill_list)
    return {
        'statusCode': 200,
        'body': json.dumps({'message':'Success!'})
    }