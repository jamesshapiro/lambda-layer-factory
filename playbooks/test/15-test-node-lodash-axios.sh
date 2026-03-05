#!/bin/bash
set -e

cd ~/code/lambda-layer-factory/test-infra/node

echo "=== Step 1: Terraform init & apply ==="
terraform init
terraform apply -auto-approve

echo ""
echo "=== Step 2: Invoke the Lambda ==="
aws lambda invoke \
  --function-name lodash-axios-test \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/lodash-axios-test-out.json

echo ""
echo "--- Response ---"
python3 -m json.tool /tmp/lodash-axios-test-out.json

echo ""
echo "=== Cleanup ==="
echo "  cd ~/code/lambda-layer-factory/test-infra/node && terraform destroy -auto-approve"
