import boto3
import datetime
import os

ec2_client = boto3.client('ec2')
iam_client = boto3.client('iam')
#ami_id = 'ami-0a8b4cd432b1c3063'
ami_id = 'ami-0ef2003049dd4c459'
instance_type = 't3.small'
key_name = 'key.pem'
subnet_id = 'subnet-c06751cf'

instance_profile_arn = os.environ['INSTANCE_PROFILE_ARN']
layer_dest_bucket = os.environ['LAYER_DEST_BUCKET']

def lambda_handler(event, context):
    token = event['token']
    my_input = event['input']
    now = datetime.datetime.now()
    datetime_str = f'{now.year}-{now.month}-{now.day}-{now.hour}:{now.minute}:{now.second}'
    # e.g. 'ulid-py'

    lib_pip_name = my_input['lib_pip_name']
    #colloquial_name = event['colloquial_name']
    # e.g. '1.1.0'
    version = my_input['version']
    python_versions = my_input['python_versions']
    init_script = [
        '#!/bin/bash',
        #'sleep 60\n'
        'cd ~\n'
        #'sudo yum update -y\n',
        #'sudo yum install ec2-instance-connect -y',
        #'sudo yum search docker',
        #'sudo yum install docker -y',
        #'sudo systemctl enable docker.service',
        #'sudo systemctl start docker.service',
        #'sudo systemctl status docker.service',
        f'echo "{lib_pip_name}=={version}" >> requirements.txt',
    ]
    # e.g. ['python3.8', 'python3.9']
    layer_publish_command = f'aws lambda publish-layer-version --layer-name {lib_pip_name}-{version.replace(".","-")}-layer-factory --description "{lib_pip_name}-{version} created by Layer Factory" --zip-file fileb://archive.zip --compatible-runtimes'
    esc_quote = r'\"'
    for python_version in python_versions:
        init_script.append(f'mkdir -p "python/lib/{python_version}/site-packages/"')
        init_script.append(f'docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-{python_version}" /bin/sh -c "pip install -r requirements.txt -t python/lib/{python_version}/site-packages/; exit"')
        layer_publish_command += f' "{python_version}"'
    layer_publish_command += ' --region "us-east-1"'
    init_script_wrapup = [
        'zip -r archive.zip python > /dev/null',
        f'aws s3 cp archive.zip s3://{layer_dest_bucket}/{lib_pip_name}-{version.replace(".","-")}-{datetime_str}.zip',
        f'aws s3 presign "s3://{layer_dest_bucket}/{lib_pip_name}' + f'-{version.replace(".","-")}-' + f'{datetime_str}.zip" --region us-east-1 --expires-in 604800 >> presigned\n'
        'export PRESIGNED_URL=$(cat presigned)',
        layer_publish_command,
        # TODO: make region configurable
        f'aws stepfunctions send-task-success --task-token "{token}" --task-output "{{{esc_quote}result{esc_quote}: {esc_quote}Success!{esc_quote}, {esc_quote}presigned_url{esc_quote}: {esc_quote}$PRESIGNED_URL{esc_quote}, {esc_quote}layer_name{esc_quote}: {esc_quote}{lib_pip_name}-{version}{esc_quote}}}" --region us-east-1',
        'shutdown -h now'
    ]
    init_script.extend(init_script_wrapup)
    init_script = '\n\n'.join(init_script)
    response = ec2_client.run_instances(
        BlockDeviceMappings=[
            {
                'DeviceName': '/dev/xvda',
                'Ebs': {
                    'Encrypted': True,
                    'DeleteOnTermination': True,
                    'VolumeSize': 16,
                    'VolumeType': 'gp2'
                },
            },
        ],
        ImageId=ami_id,
        InstanceType=instance_type,
        IamInstanceProfile={
            'Arn': instance_profile_arn
        },
        #KeyName=key_name,
        SubnetId=subnet_id,
        MaxCount=1,
        MinCount=1,
        InstanceInitiatedShutdownBehavior='terminate', 
        UserData=init_script,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'APPLICATION',
                        'Value': 'CDK_LAMBDA_LAYER_FACTORY'
                    },
                ]
            },
        ],
    )
    instance = response['Instances'][0]
    instance_id = instance['InstanceId']
    return {"result": "success creating EC2 instance", "instance_id": instance_id}