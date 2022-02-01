from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    Stack,
    aws_s3 as s3,
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as tasks,
    aws_apigateway as apigateway,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
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
            self, "cdk-layer-factory-bucket",
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        ec2_role = iam.Role(self, "cdk-layer-factory-ec2-role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="Allow EC2 instance to write to layer S3 bucket and publish layer versions to Lambda"
        )

        ec2_policy = iam.Policy(
            self, 'cdk-layer-factory-ec2-s3-write-layer-publish-policy',
            statements=[
                iam.PolicyStatement(
                    actions=['s3:PutObject'],
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

        ec2_role.attach_inline_policy(ec2_policy)
        cfn_instance_profile = iam.CfnInstanceProfile(self, "MyCfnInstanceProfile",
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

        start_ec2_state = tasks.LambdaInvoke(self, "Start EC2",
            lambda_function=start_layer_creation_function_cdk,
            integration_pattern=stepfunctions.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload=stepfunctions.TaskInput.from_object({
                "token": stepfunctions.JsonPath.task_token,
                "input": stepfunctions.JsonPath.string_at("$")
            }),
            result_path="$.taskresult",
            timeout=Duration.hours(1)
        )

        topic = sns.Topic(self, "CDKLambdaFactoryTopic")
        topic.add_subscription(subscriptions.EmailSubscription(email))

        email_recipient_state = tasks.SnsPublish(self, "Send Email",
            topic=topic,
            message=stepfunctions.TaskInput.from_json_path_at("$.taskresult.message"),
        )

        definition = start_ec2_state.next(email_recipient_state)

        state_machine = stepfunctions.StateMachine(self, "cdk-sfn-demo-state-machine",
            definition=definition
        )

        api = apigateway.RestApi(
            self,
            'cdk-lambda-layer-factory-api',
            description='CDK Lambda Layer Factory.'
        )

        credentials_role = iam.Role(
            self, 'cdk-sfn-demo-trigger-state-machine-role',
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
        )

        trigger_state_machine_policy = iam.Policy(
            self, 'cdk-sfn-demo-trigger-state-machine-policy',
            statements=[iam.PolicyStatement(
                actions=['states:StartExecution'],
                resources=[state_machine.state_machine_arn]
            )]
        )
        credentials_role.attach_inline_policy(trigger_state_machine_policy)

        entry_point = api.root.add_resource("create-layer")
        entry_point.add_method(
            'POST',
            integration=apigateway.AwsIntegration(
                service='states',
                action="StartExecution",
                integration_http_method="POST",
                options=apigateway.IntegrationOptions(
                    credentials_role=credentials_role,
                    request_templates={
                        "application/json": f'{{"input": "$util.escapeJavaScript($input.body)", "stateMachineArn": "{state_machine.state_machine_arn}"}}'
                    },
                    integration_responses=[
                        apigateway.IntegrationResponse(status_code="200")
                    ],
                )
            ),
            method_responses=[apigateway.MethodResponse(status_code="200")]
        )

        cdk.CfnOutput(
            self, "StepFunctionsApi",
            description="CDK Lambda Factory Entry Point API",
            value = f'https://{api.rest_api_id}.execute-api.us-east-1.amazonaws.com/prod/create-layer/'
        )


