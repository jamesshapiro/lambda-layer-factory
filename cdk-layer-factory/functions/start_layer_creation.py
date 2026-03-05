import boto3
import datetime
import os
import sys
import hashlib

ec2_client = boto3.client('ec2')
iam_client = boto3.client('iam')
ddb_client = boto3.client('dynamodb')
ami_id = 'ami-0ef2003049dd4c459'
instance_type = 't3.small'
key_name = 'key.pem'
subnet_id = 'subnet-c06751cf'

instance_profile_arn = os.environ['INSTANCE_PROFILE_ARN']
layer_dest_bucket = os.environ['LAYER_DEST_BUCKET']


def get_wrapup_commands(zip_dir, layer_name, datetime_str, runtimes, token, auto_publish, publish_regions, layer_suffix):
    esc_quote = r'\"'
    runtimes_str = ' '.join(runtimes)
    commands = [
        f'zip -r archive.zip {zip_dir} > /dev/null',
        f'aws s3 cp archive.zip s3://{layer_dest_bucket}/{layer_name}-{datetime_str}.zip',
        f'aws s3 presign "s3://{layer_dest_bucket}/{layer_name}' + f'-' + f'{datetime_str}.zip" --region us-east-1 --expires-in 604800 >> presigned\n'
        'export PRESIGNED_URL=$(cat presigned)',
    ]
    if auto_publish and publish_regions:
        commands.append('export LAYER_ARN="N/A"')
        for region in publish_regions:
            commands.append(
                f'PUBLISH_OUTPUT=$(aws lambda publish-layer-version'
                f' --layer-name {layer_name}{layer_suffix}'
                f' --description "{layer_name} created by Layer Factory"'
                f' --content S3Bucket={layer_dest_bucket},S3Key={layer_name}-{datetime_str}.zip'
                f' --compatible-runtimes {runtimes_str}'
                f' --region {region})'
            )
            commands.append(
                f'export LAYER_ARN=$(echo "$PUBLISH_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)[\'LayerVersionArn\'])")'
            )
        task_output = f'{{{esc_quote}result{esc_quote}: {esc_quote}Success!{esc_quote}, {esc_quote}presigned_url{esc_quote}: {esc_quote}$PRESIGNED_URL{esc_quote}, {esc_quote}layer_name{esc_quote}: {esc_quote}{layer_name}{esc_quote}, {esc_quote}s3_key{esc_quote}: {esc_quote}{layer_name}-{datetime_str}.zip{esc_quote}, {esc_quote}layer_arn{esc_quote}: {esc_quote}$LAYER_ARN{esc_quote}}}'
    else:
        task_output = f'{{{esc_quote}result{esc_quote}: {esc_quote}Success!{esc_quote}, {esc_quote}presigned_url{esc_quote}: {esc_quote}$PRESIGNED_URL{esc_quote}, {esc_quote}layer_name{esc_quote}: {esc_quote}{layer_name}{esc_quote}, {esc_quote}s3_key{esc_quote}: {esc_quote}{layer_name}-{datetime_str}.zip{esc_quote}, {esc_quote}layer_arn{esc_quote}: {esc_quote}N/A{esc_quote}}}'
    commands.extend([
        f'aws stepfunctions send-task-success --task-token "{token}" --task-output "{task_output}" --region us-east-1',
        f'aws s3 cp /tmp/build.log s3://{layer_dest_bucket}/logs/{layer_name}-{datetime_str}.log --region us-east-1',
        'shutdown -h now'
    ])
    return commands


def get_python_commands(runtimes, dependencies, layer_name, token, datetime_str, auto_publish=False, publish_regions=None, layer_suffix='-layer-factory'):
    if publish_regions is None:
        publish_regions = []
    init_script = ['#!/bin/bash\nset -x\nexec > /tmp/build.log 2>&1','cd ~\n']
    for dependency in dependencies:
        init_script.append(f'echo "{dependency}" >> requirements.txt\n')
    for runtime in runtimes:
        init_script.append(f'mkdir -p "python/lib/{runtime}/site-packages/"')
        init_script.append(f'docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-{runtime}" /bin/sh -c "pip install -r requirements.txt -t python/lib/{runtime}/site-packages/; exit"')
    init_script.extend(get_wrapup_commands('python', layer_name, datetime_str, runtimes, token, auto_publish, publish_regions, layer_suffix))
    return '\n\n'.join(init_script)


def get_node_commands(runtimes, dependencies, layer_name, token, datetime_str, auto_publish=False, publish_regions=None, layer_suffix='-layer-factory'):
    if publish_regions is None:
        publish_regions = []
    init_script = ['#!/bin/bash\nset -x\nexec > /tmp/build.log 2>&1', 'cd ~\n']
    init_script.append('mkdir -p nodejs')
    build_runtime = runtimes[0]
    # Convert "library==version" to "library@version" for npm
    node_deps = []
    for dep in dependencies:
        dep = dep.strip()
        if '==' in dep:
            name, ver = dep.split('==', 1)
            node_deps.append(f'{name}@{ver}')
        else:
            node_deps.append(dep)
    deps_str = ' '.join(node_deps)
    init_script.append(
        f'docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-{build_runtime}" '
        f'/bin/sh -c "cd nodejs && npm install {deps_str}; exit"'
    )
    init_script.extend(get_wrapup_commands('nodejs', layer_name, datetime_str, runtimes, token, auto_publish, publish_regions, layer_suffix))
    return '\n\n'.join(init_script)


def get_ruby_commands(runtimes, dependencies, layer_name, token, datetime_str, auto_publish=False, publish_regions=None, layer_suffix='-layer-factory'):
    if publish_regions is None:
        publish_regions = []
    init_script = ['#!/bin/bash\nset -x\nexec > /tmp/build.log 2>&1', 'cd ~\n']
    # Convert "library==version" to "library -v version" for gem
    gem_args = []
    for dep in dependencies:
        dep = dep.strip()
        if '==' in dep:
            name, ver = dep.split('==', 1)
            gem_args.append(f'{name} -v {ver}')
        else:
            gem_args.append(dep)
    deps_str = ' '.join(gem_args)
    for runtime in runtimes:
        version = runtime.replace('ruby', '')
        gem_path = f'ruby/gems/{version}.0'
        init_script.append(f'mkdir -p "{gem_path}"')
        init_script.append(
            f'docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-{runtime}" '
            f'/bin/sh -c "gem install {deps_str} --install-dir /var/task/{gem_path} --no-document; exit"'
        )
    init_script.extend(get_wrapup_commands('ruby', layer_name, datetime_str, runtimes, token, auto_publish, publish_regions, layer_suffix))
    return '\n\n'.join(init_script)


def get_java_commands(runtimes, dependencies, layer_name, token, datetime_str, auto_publish=False, publish_regions=None, layer_suffix='-layer-factory'):
    if publish_regions is None:
        publish_regions = []
    init_script = ['#!/bin/bash\nset -x\nexec > /tmp/build.log 2>&1', 'cd ~\n']
    init_script.append('mkdir -p java/lib')
    # Dependencies expected in groupId:artifactId:version format
    dep_xml = ''
    for dep in dependencies:
        parts = dep.strip().split(':')
        if len(parts) >= 3:
            dep_xml += f'<dependency><groupId>{parts[0]}</groupId><artifactId>{parts[1]}</artifactId><version>{parts[2]}</version></dependency>'
    pom = f'<?xml version="1.0"?><project><modelVersion>4.0.0</modelVersion><groupId>com.layerfactory</groupId><artifactId>layer</artifactId><version>1.0</version><dependencies>{dep_xml}</dependencies></project>'
    init_script.append(f"cat > pom.xml << 'POMEOF'\n{pom}\nPOMEOF")
    build_runtime = runtimes[0]
    init_script.append(
        f'docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-{build_runtime}" '
        f'/bin/sh -c "mvn dependency:copy-dependencies -DoutputDirectory=java/lib -f pom.xml; exit"'
    )
    init_script.extend(get_wrapup_commands('java', layer_name, datetime_str, runtimes, token, auto_publish, publish_regions, layer_suffix))
    return '\n\n'.join(init_script)


def lambda_handler(event, context):
    token = event['token']
    my_input = event['input']
    now = datetime.datetime.now()
    datetime_str = f'{now.year}-{now.month}-{now.day}-{now.hour}:{now.minute}:{now.second}'

    dependencies = my_input['dependencies'].split(',')
    layer_name = my_input['layer_name']
    runtimes = my_input['runtimes']
    language = my_input['language']
    auto_publish = my_input.get('auto_publish', False)
    publish_regions = my_input.get('publish_regions', [])
    email = my_input.get('email', '')
    layer_suffix = '-lf' if email == 'james.shapiro@gmail.com' else '-layer-factory'

    build_args = (runtimes, dependencies, layer_name, token, datetime_str, auto_publish, publish_regions, layer_suffix)
    if language == 'python':
        init_script = get_python_commands(*build_args)
    elif language == 'node':
        init_script = get_node_commands(*build_args)
    elif language == 'ruby':
        init_script = get_ruby_commands(*build_args)
    elif language == 'java':
        init_script = get_java_commands(*build_args)
    else:
        raise ValueError(f'Unsupported language for layer building: {language}')
    response = ec2_client.run_instances(
        BlockDeviceMappings=[
            {
                'DeviceName': '/dev/xvda',
                'Ebs': {
                    'Encrypted': True,
                    'DeleteOnTermination': True,
                    'VolumeSize': 32,
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