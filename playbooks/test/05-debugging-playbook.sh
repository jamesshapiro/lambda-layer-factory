#!/bin/bash

# Check publish_layer logs
aws logs tail /aws/lambda/layer-factory-publish-layer --since 30m --format short

# Check start_layer_creation logs
aws logs tail /aws/lambda/layer-factory-start-layer-creation --since 30m --format short

# Check send_email logs
aws logs tail /aws/lambda/layer-factory-send-email --since 30m --format short

# Check if any EC2 build instances are still running
aws ec2 describe-instances \
  --filters "Name=tag:APPLICATION,Values=CDK_LAMBDA_LAYER_FACTORY,LAMBDA_LAYER_FACTORY" "Name=instance-state-name,Values=running,stopped" \
  --query "Reservations[].Instances[].[InstanceId,State.Name,LaunchTime]" \
  --output table

# Check latest layer zips in S3
aws s3 ls s3://layer-factory/ --human-readable | sort -k1,2 | tail -10

# Check step function executions
aws stepfunctions list-executions \
  --state-machine-arn $(aws stepfunctions list-state-machines --query "stateMachines[?contains(name,'layer-factory')].stateMachineArn" --output text) \
  --max-results 5 \
  --output table

# ---

aws lambda get-function-configuration --function-name layer-factory-start-layer-creation --query "CodeSha256" --output text

grep lambda_code_object_version ~/code/terragrunt-infrastructure-live/athens/us-east-1/default/lambda-layer-factory-backend-v2/terragrunt.hcl

# ---

# Check EC2 build logs
aws s3 ls s3://layer-factory/logs/ --human-readable | sort -k1,2 | tail -5

# Download latest build log
aws s3 cp "$(aws s3 ls s3://layer-factory/logs/ | sort -k1,2 | tail -1 | awk '{print "s3://layer-factory/logs/"$4}')" /tmp/build.log && cat /tmp/build.log
