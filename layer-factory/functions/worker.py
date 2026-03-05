import queue
import boto3
import os
import json

sqs_client = boto3.client('sqs')
stepfunctions_client = boto3.client('stepfunctions')
queue_url = os.environ['QUEUE_URL']

def lambda_handler(event, context):
    my_region = os.environ['EC2_REGION']
    ec2_client = boto3.client('ec2', region_name=my_region)
    response = ec2_client.describe_instances()['Reservations']
    concurrency_limit = int(os.environ['CONCURRENCY_LIMIT'])
    num_layers_being_built = 0
    for reservation in response:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            if instance['State']['Name'] == 'terminated':
                continue
            if 'Tags' in instance:
                tags = instance['Tags']
                for tag in tags:
                    if tag['Key'] == 'APPLICATION' and tag['Value'] == 'CDK_LAMBDA_LAYER_FACTORY':
                        num_layers_being_built += 1
    if num_layers_being_built >= concurrency_limit:
        return
    messages = sqs_client.receive_message(
        QueueUrl=queue_url,
    )
    if 'Messages' not in messages:
        return
    message = messages['Messages'][0]
    receipt_handle = message['ReceiptHandle']
    body = json.loads(message['Body'])
    token = body['token']
    try:
        response = stepfunctions_client.send_task_success(
            taskToken=token,
            output=json.dumps({'result':'continue'})
        )
        print(f'{response=}')
    except:
        pass
    response = sqs_client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )