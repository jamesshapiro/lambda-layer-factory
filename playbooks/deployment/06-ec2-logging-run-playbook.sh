#!/bin/bash
set -e

cd ~/code/lambda-layer-factory/layer-factory/functions
zip archive.zip check_cache.py get_hash.py reap_instances.py send_email.py publish_layer.py start_layer_creation.py worker.py
aws s3 cp archive.zip s3://athens-build-lambda-code/lambda-layer-factory/archive.zip

VERSION_ID=$(aws s3api head-object --bucket athens-build-lambda-code --key lambda-layer-factory/archive.zip --query VersionId --output text)
echo "New VersionId: $VERSION_ID"

cd ~/code/terragrunt-infrastructure-live/athens/us-east-1/default/lambda-layer-factory-backend-v2
sed -i "s/lambda_code_object_version = \".*\"/lambda_code_object_version = \"$VERSION_ID\"/" terragrunt.hcl
terragrunt apply -auto-approve

echo ""
echo "=== Deployed. Submit a Ruby 3.3 build via demo.lambdalayerfactory.com ==="
echo "=== Then run these to inspect: ==="
echo ""
echo "aws s3 ls s3://layer-factory/logs/ --human-readable | sort -k1,2 | tail -5"
echo "aws s3 cp \"\$(aws s3 ls s3://layer-factory/logs/ | sort -k1,2 | tail -1 | awk '{print \"s3://layer-factory/logs/\"\$4}')\" /tmp/build.log && cat /tmp/build.log"
echo "aws s3 ls s3://layer-factory/ --human-readable | sort -k1,2 | tail -5"
