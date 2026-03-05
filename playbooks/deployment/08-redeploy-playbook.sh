#!/bin/bash
set -e

echo "=== Step 1: Package and upload Lambda code ==="
cd ~/code/lambda-layer-factory/cdk-layer-factory/functions
zip archive.zip check_cache.py get_hash.py reap_instances.py send_email.py publish_layer.py start_layer_creation.py worker.py
aws s3 cp archive.zip s3://athens-build-lambda-code/lambda-layer-factory/archive.zip

VERSION_ID=$(aws s3api head-object --bucket athens-build-lambda-code --key lambda-layer-factory/archive.zip --query VersionId --output text)
echo "New VersionId: $VERSION_ID"

echo ""
echo "=== Step 2: Update terragrunt.hcl and apply ==="
cd ~/code/terragrunt-infrastructure-live/athens/us-east-1/default/lambda-layer-factory-backend-v2
sed -i "s/lambda_code_object_version = \".*\"/lambda_code_object_version = \"$VERSION_ID\"/" terragrunt.hcl
terragrunt apply -auto-approve

echo ""
echo "=== Deployed! ==="
echo ""
echo "To bust the cache and retest, run:"
echo "  cd ~/code/lambda-layer-factory/playbooks/test/07-uv-env && uv run 07-bust-cache-and-retest.py"
echo ""
echo "Then submit a fresh build via demo.lambdalayerfactory.com"
echo ""
echo "To check EC2 build logs after:"
echo "  aws s3 ls s3://layer-factory/logs/ --human-readable | sort -k1,2 | tail -5"
echo "  aws s3 cp \"\$(aws s3 ls s3://layer-factory/logs/ | sort -k1,2 | tail -1 | awk '{print \"s3://layer-factory/logs/\"\$4}')\" /tmp/build.log && cat /tmp/build.log"
