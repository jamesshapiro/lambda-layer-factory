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
    aws_sqs as sqs,
    aws_certificatemanager as certificatemanager,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    Aws, CfnOutput, Duration
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
            email = [line for line in lines if line.startswith('email=')][0].split('=')[1]
            sender = [line for line in lines if line.startswith('sender=')][0].split('=')[1]
            subdomain = [line for line in lines if line.startswith('subdomain=')][0].split('=')[1]
            lambda_layer_factory_dot_com_zone = [line for line in lines if line.startswith('lambda_layer_factory_dot_com_zone=')][0].split('=')[1]
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

        job_queue = sqs.Queue(self, "JobQueue")

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
            code=lambda_.Code.from_asset('functions'),
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
            code=lambda_.Code.from_asset('functions'),
            handler='check_cache.lambda_handler',
            timeout=Duration.seconds(25),
            environment={
                'DDB_TABLE_NAME': ddb_table.table_name,
                'S3_BUCKET': layer_bucket.bucket_name
            },
        )

        worker_lambda = worker_function_cdk = lambda_.Function(
            self, 'cdk-layer-factory-worker',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('functions'),
            handler='worker.lambda_handler',
            timeout=Duration.seconds(15),
            environment={
                'QUEUE_URL': job_queue.queue_url,
                'EC2_REGION': Aws.REGION,
                'CONCURRENCY_LIMIT': '1'
            }
        )
        
        layer_bucket.grant_read(check_cache_function_cdk)
        ddb_table.grant_read_data(check_cache_function_cdk)

        reap_ec2_instances_function_cdk = lambda_.Function(
            self, 'cdk-layer-factory-reap-instances',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('functions'),
            handler='reap_instances.lambda_handler',
            timeout=Duration.seconds(120),
            memory_size=128,
            environment={
                'EC2_REGION': Aws.REGION
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

        lambda_ec2_worker_policy = iam.Policy(
            self, 'cdk-layer-factory-lambda-ec2-worker-policy',
            statements=[
                iam.PolicyStatement(
                    actions=['ec2:DescribeInstances'],
                    resources=['*']
                ),
                iam.PolicyStatement(
                    actions=['states:SendTaskSuccess'],
                    resources=['*']
                )
            ]
        )

        reap_ec2_instances_function_cdk.role.attach_inline_policy(lambda_ec2_reaper_policy)
        worker_function_cdk.role.attach_inline_policy(lambda_ec2_worker_policy)
        reaper_lambda_target = targets.LambdaFunction(reap_ec2_instances_function_cdk)
        worker_lambda_target = targets.LambdaFunction(worker_function_cdk)

        events.Rule(self, 'EC2ReaperSchedule',
            schedule=events.Schedule.cron(minute='7/10', hour='*'),
            targets=[reaper_lambda_target]
        )

        events.Rule(self, 'EC2WorkerSchedule',
            schedule=events.Schedule.cron(minute='*', hour='*'),
            targets=[worker_lambda_target]
        )

        ec2_role.attach_inline_policy(ec2_policy)
        cfn_instance_profile = iam.CfnInstanceProfile(self, 'MyCfnInstanceProfile',
            roles=[ec2_role.role_name]
        )

        start_layer_creation_function_cdk = lambda_.Function(
            self, 'cdk-layer-factory-start-creation',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('functions'),
            handler='start_layer_creation.lambda_handler',
            timeout=Duration.seconds(120),
            memory_size=128,
            environment={
                'INSTANCE_PROFILE_ARN': cfn_instance_profile.attr_arn,
                'LAYER_DEST_BUCKET': layer_bucket.bucket_name
            }
        )

        job_queue.grant_consume_messages(worker_lambda)

        start_layer_creation_function_cdk.role.attach_inline_policy(run_ec2_lambda_policy)

        topic = sns.Topic(self, 'CDKLambdaFactoryTopic')
        topic.add_subscription(subscriptions.EmailSubscription(email))

        check_cache_kwargs = {
            "lambda_function":check_cache_function_cdk,
            "payload":stepfunctions.TaskInput.from_object({
                'input': stepfunctions.JsonPath.string_at('$')
            }),
            "result_selector":{
                'presigned_url': stepfunctions.JsonPath.string_at('$.Payload.presigned_url')
            },
            "result_path":'$.taskresult',
            "timeout":Duration.minutes(1)
        }

        check_cache_state_1 = tasks.LambdaInvoke(self, 'Check Cache 1',
            **check_cache_kwargs
        )

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
            'iam_resources':[f'arn:aws:ses:{Aws.REGION}:{Aws.ACCOUNT_ID}:identity/{sender}']
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

        check_cache_2_choice_state = stepfunctions.Choice(self, 'Is It Cached Post-Queue?')
        handle_uncached_2 = start_ec2_state
        handle_cached_2 = email_and_terminate
        #handle_cached_2 = start_ec2_state
        check_cache_2_choice_state.when(stepfunctions.Condition.string_equals('$.taskresult.presigned_url','NOT FOUND!'), handle_uncached_2)
        check_cache_2_choice_state.otherwise(handle_cached_2)

        check_cache_state_2 = tasks.LambdaInvoke(self, 'Check Cache 2',
            **check_cache_kwargs
        ).next(check_cache_2_choice_state)

        queue_state = tasks.SqsSendMessage(self, "Queue",
            queue = job_queue,
            integration_pattern=stepfunctions.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            message_body=stepfunctions.TaskInput.from_object({
                "token": stepfunctions.JsonPath.task_token
            }),
            result_path='$.queueresult',
        ).next(check_cache_state_2)

        check_cache_1_choice_state = stepfunctions.Choice(self, 'Is It Cached Pre-Queue?')
        handle_uncached_1 = queue_state
        handle_cached_1 = email_and_terminate
        #handle_cached_1 = queue_state
        check_cache_1_choice_state.when(stepfunctions.Condition.string_equals('$.taskresult.presigned_url','NOT FOUND!'), handle_uncached_1)
        check_cache_1_choice_state.otherwise(handle_cached_1)

        definition = get_hash_state.next(check_cache_state_1).next(check_cache_1_choice_state)

        state_machine = stepfunctions.StateMachine(self, 'cdk-lambda-layer-factory-state-machine',
            definition=definition
        )

        api = apigateway.RestApi(
            self,
            'cdk-lambda-layer-factory-api',
            description='CDK Lambda Layer Factory.',
            deploy_options=apigateway.StageOptions(
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS
            )
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

        entry_point = api.root.add_resource('create-layer',
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST"]
            )
        )

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


        ######## FRONT-END WEBSITE ########
        zone = route53.HostedZone.from_hosted_zone_attributes(self, "HostedZone",
            hosted_zone_id=lambda_layer_factory_dot_com_zone,
            zone_name=subdomain
        )

        site_bucket = s3.Bucket(
            self, f'{subdomain}-bucket',
        )
        certificate = certificatemanager.DnsValidatedCertificate(
            self, f'{subdomain}-certificate',
            domain_name=subdomain,
            hosted_zone=zone,
            subject_alternative_names=[f'www.{subdomain}']
        )
        
        domain_names = [subdomain, f'www.{subdomain}']
        server_router_function = cloudfront.experimental.EdgeFunction(self, "ServerRouter",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset('lambda_edge'),
            handler='server_router.lambda_handler',
        )
        
        distribution = cloudfront.Distribution(
            self, f'{subdomain}-distribution',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(site_bucket),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                edge_lambdas=[
                    cloudfront.EdgeLambda(
                        function_version=server_router_function.current_version,
                        event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
                    )
                ]
            ),
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(30)
                )
            ],
            comment=f'{subdomain} S3 HTTPS',
            default_root_object='index.html',
            domain_names=domain_names,
            certificate=certificate
        )

        CfnOutput(self, f'{subdomain}-cf-distribution', value=distribution.distribution_id)
        a_record_target = route53.RecordTarget.from_alias(route53_targets.CloudFrontTarget(distribution))
        record = route53.ARecord(
            self, f'{subdomain}-alias-record',
            zone=zone,
            target=a_record_target,
            record_name=subdomain
        )
        CfnOutput(self, f'{subdomain}-bucket-name', value=site_bucket.bucket_name)
        # www.lambdalayerfactory.com -> lambdalayerfactory.com
        a_record_target = route53.RecordTarget.from_alias(route53_targets.Route53RecordTarget(record))
        route53.CnameRecord(
            self, f'www-{subdomain}-alias-record',
            zone=zone,
            domain_name=f'{subdomain}.',
            record_name=f'www.{subdomain}'
        )


