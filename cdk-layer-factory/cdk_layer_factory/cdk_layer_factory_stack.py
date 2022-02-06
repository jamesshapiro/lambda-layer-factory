from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as tasks,
    aws_apigateway as apigateway,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_events as events,
    aws_events_targets as targets,
)

import aws_cdk as cdk

from constructs import Construct

class CdkLayerFactoryStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        with open('.cdk-params') as f:
            lines = f.read().splitlines()
            # .cdk-params should be of the form:
            # account_id=12345678901234
            account_id = [line for line in lines if line.startswith('account_id')][0].split('=')[1]
            email = [line for line in lines if line.startswith('email')][0].split('=')[1]
            sender = [line for line in lines if line.startswith('sender')][0].split('=')[1]
            region = [line for line in lines if line.startswith('region')][0].split('=')[1]
        run_ec2_lambda_policy = iam.Policy(
            self, 'cdk-layer-factory-start-creation-policy',
            statements=[
                # TODO: limit ec2 permissions
                iam.PolicyStatement(
                    actions=['ec2:*'],
                    resources=['*']
                ),
                # TODO: limit PassRole to the ec2 role
                iam.PolicyStatement(
                    actions=['iam:PassRole'],
                    resources=['*']
                ),
                
            ]
        )

        layer_bucket = s3.Bucket(
            self, 'cdk-layer-factory-bucket',
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        ec2_role = iam.Role(self, 'cdk-layer-factory-ec2-role',
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            description='Allow EC2 instance to write to layer S3 bucket and publish layer versions to Lambda'
        )

        ec2_policy = iam.Policy(
            self, 'cdk-layer-factory-ec2-s3-write-layer-publish-policy',
            statements=[
                iam.PolicyStatement(
                    actions=['s3:PutObject', 's3:GetObject'],
                    resources=[layer_bucket.bucket_arn, f'{layer_bucket.bucket_arn}/*']
                ),
                iam.PolicyStatement(
                    actions=['lambda:PublishLayerVersion'],
                    resources=['*']
                ),
                # TODO: potentially narrow this with custom resources
                iam.PolicyStatement(
                    actions=['states:SendTaskSuccess','states:SendTaskFailure'],
                    resources=['*']
                ),
            ]
        )

        pytz_layer = lambda_.LayerVersion(
            self, 'pytz-layer',
            removal_policy=cdk.RemovalPolicy.DESTROY,
            code=lambda_.Code.from_asset('layers/pytz-2021.1.zip'),
            compatible_architectures=[lambda_.Architecture.X86_64]
        )

        ulid_layer = lambda_.LayerVersion(
            self, 'ulid-layer',
            removal_policy=cdk.RemovalPolicy.DESTROY,
            code=lambda_.Code.from_asset('layers/ulid-1.1.0.zip'),
            compatible_architectures=[lambda_.Architecture.X86_64]
        )

        get_hash_function_cdk = lambda_.Function(
            self, 'cdk-layer-factory-get-hash',
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset('resources'),
            handler='get_hash.lambda_handler',
            timeout=Duration.seconds(10),
            layers=[ulid_layer]
        )

        ddb_table = dynamodb.Table(
            self, 'Table',
            partition_key=dynamodb.Attribute(name='PK1', type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        check_cache_function_cdk = lambda_.Function(
            self, 'cdk-layer-factory-check-cache',
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset('resources'),
            handler='check_cache.lambda_handler',
            timeout=Duration.seconds(25),
            environment={
                'DDB_TABLE_NAME': ddb_table.table_name,
                'S3_BUCKET': layer_bucket.bucket_name
            },
        )
        
        layer_bucket.grant_read(check_cache_function_cdk)
        ddb_table.grant_read_data(check_cache_function_cdk)

        reap_ec2_instances_function_cdk = lambda_.Function(
            self, 'cdk-layer-factory-reap-instances',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('resources'),
            handler='reap_instances.lambda_handler',
            timeout=Duration.seconds(120),
            memory_size=128,
            environment={
                'EC2_REGION': region
            },
            layers=[pytz_layer]
        )

        lambda_ec2_reaper_policy = iam.Policy(
            self, 'cdk-layer-factory-lambda-ec2-reaper-policy',
            statements=[
                iam.PolicyStatement(
                    actions=['ec2:TerminateInstances'],
                    resources=['*'],
                    conditions={
                        'StringEquals': {'ec2:ResourceTag/APPLICATION': 'CDK_LAMBDA_LAYER_FACTORY'} 
                    }
                ),
                iam.PolicyStatement(
                    actions=['ec2:DescribeInstances'],
                    resources=['*']
                )
            ]
        )

        reap_ec2_instances_function_cdk.role.attach_inline_policy(lambda_ec2_reaper_policy)
        lambda_target = targets.LambdaFunction(reap_ec2_instances_function_cdk)

        events.Rule(self, 'EC2ReaperSchedule',
            schedule=events.Schedule.cron(minute='7/10', hour='*'),
            targets=[lambda_target]
        )

        ec2_role.attach_inline_policy(ec2_policy)
        cfn_instance_profile = iam.CfnInstanceProfile(self, 'MyCfnInstanceProfile',
            roles=[ec2_role.role_name]
        )

        start_layer_creation_function_cdk = lambda_.Function(
            self, 'cdk-layer-factory-start-creation',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('resources'),
            handler='start_layer_creation.lambda_handler',
            timeout=Duration.seconds(120),
            memory_size=128,
            environment={
                'INSTANCE_PROFILE_ARN': cfn_instance_profile.attr_arn,
                'LAYER_DEST_BUCKET': layer_bucket.bucket_name
            }
        )
        start_layer_creation_function_cdk.role.attach_inline_policy(run_ec2_lambda_policy)

        topic = sns.Topic(self, 'CDKLambdaFactoryTopic')
        topic.add_subscription(subscriptions.EmailSubscription(email))

        kwargs = {
            'service':'ses',
            'action':'sendEmail',
            'parameters': {
                'Destination': {
                    'ToAddresses': stepfunctions.JsonPath.array(stepfunctions.JsonPath.string_at('$.email'))
                },
                'Message': {
                    'Body': {
                        'Html': {
                            'Data': stepfunctions.JsonPath.format('<html><h3>Lambda Layer Created!</h3><p>Click <a href="{}">here</a> to download. Link is good for 6 hours. If it expires, just invoke the factory again to receive a new link.</p>', stepfunctions.JsonPath.string_at("$.taskresult.presigned_url"))
                        }
                    },
                    'Subject': {
                        'Data': stepfunctions.JsonPath.format('{} CREATED! (Run-ID: {})', stepfunctions.JsonPath.string_at('$.layer_name'), stepfunctions.JsonPath.string_at('$.hashresult.ulid'))
                    }
                },
                'Source': f'Layer Factory Update <{sender}>'
            },
            'iam_action':'ses:SendEmail',
            'result_path':'$.emailresult',
            'iam_resources':[f'arn:aws:ses:{region}:{account_id}:identity/{sender}']
        }

        email_recipient_state = tasks.CallAwsService(self, 'SendEmail',**kwargs)
        email_and_terminate = email_recipient_state

        get_hash_state = tasks.LambdaInvoke(self, 'Get Hash',
            lambda_function=get_hash_function_cdk,
            payload=stepfunctions.TaskInput.from_object({
                'input': stepfunctions.JsonPath.string_at('$')
            }),
            result_selector={
                'layer_hash': stepfunctions.JsonPath.string_at('$.Payload.layer_hash'),
                'ulid': stepfunctions.JsonPath.string_at('$.Payload.ulid'),
            },
            result_path='$.hashresult',
            timeout=Duration.minutes(1)
        )

        check_cache_state = tasks.LambdaInvoke(self, 'Check Cache',
            lambda_function=check_cache_function_cdk,
            payload=stepfunctions.TaskInput.from_object({
                'input': stepfunctions.JsonPath.string_at('$')
            }),
            result_selector={
                'presigned_url': stepfunctions.JsonPath.string_at('$.Payload.presigned_url')
            },
            result_path='$.taskresult',
            timeout=Duration.minutes(1)
        )

        cache_layer_state = tasks.DynamoPutItem(self, 'Cache Layer',
            item={
                'PK1': tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at('$.hashresult.layer_hash')),
                'S3_BUCKET': tasks.DynamoAttributeValue.from_string(layer_bucket.bucket_name),
                'S3_KEY': tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at('$.taskresult.s3_key')),
            },
            table=ddb_table,
            result_path='$.ddb_result'
        )

        email_and_terminate = tasks.CallAwsService(self, 'Send Cached Email',**kwargs)
        email_and_cache = tasks.CallAwsService(self, 'Send Uncached Email',**kwargs).next(cache_layer_state)

        start_ec2_state = tasks.LambdaInvoke(self, 'Start EC2',
            lambda_function=start_layer_creation_function_cdk,
            integration_pattern=stepfunctions.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload=stepfunctions.TaskInput.from_object({
                'token': stepfunctions.JsonPath.task_token,
                'input': stepfunctions.JsonPath.string_at('$')
            }),
            result_path='$.taskresult',
            timeout=Duration.hours(1)
        ).next(email_and_cache)

        is_cached_choice_state = stepfunctions.Choice(self, 'Is It Cached?')
        handle_uncached = start_ec2_state
        #handle_cached = start_ec2_state
        handle_cached = email_and_terminate
        is_cached_choice_state.when(stepfunctions.Condition.string_equals('$.taskresult.presigned_url','NOT FOUND!'), handle_uncached)
        is_cached_choice_state.otherwise(handle_cached)
        definition = get_hash_state.next(check_cache_state).next(is_cached_choice_state)

        state_machine = stepfunctions.StateMachine(self, 'cdk-lambda-layer-factory-state-machine',
            definition=definition
        )

        api = apigateway.RestApi(
            self,
            'cdk-lambda-layer-factory-api',
            description='CDK Lambda Layer Factory.'
        )

        credentials_role = iam.Role(
            self, 'cdk-sfn-demo-trigger-state-machine-role',
            assumed_by=iam.ServicePrincipal('apigateway.amazonaws.com'),
        )

        trigger_state_machine_policy = iam.Policy(
            self, 'cdk-sfn-demo-trigger-state-machine-policy',
            statements=[iam.PolicyStatement(
                actions=['states:StartExecution'],
                resources=[state_machine.state_machine_arn]
            )]
        )
        credentials_role.attach_inline_policy(trigger_state_machine_policy)

        entry_point = api.root.add_resource('create-layer')
        entry_point.add_method(
            'POST',
            integration=apigateway.AwsIntegration(
                service='states',
                action='StartExecution',
                integration_http_method='POST',
                options=apigateway.IntegrationOptions(
                    credentials_role=credentials_role,
                    request_templates={
                        'application/json': f'{{"input": "$util.escapeJavaScript($input.body)", "stateMachineArn": "{state_machine.state_machine_arn}"}}'
                    },
                    integration_responses=[
                        apigateway.IntegrationResponse(status_code='200')
                    ],
                )
            ),
            method_responses=[apigateway.MethodResponse(status_code='200')]
        )

        cdk.CfnOutput(
            self, 'StepFunctionsApi',
            description='CDK Lambda Factory Entry Point API',
            value = f'https://{api.rest_api_id}.execute-api.us-east-1.amazonaws.com/prod/create-layer/'
        )


