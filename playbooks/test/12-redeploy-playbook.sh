#!/bin/bash
set -e

URL="${1:-https://aws.amazon.com}"

cd ~/code/lambda-layer-factory/test-infra

echo "=== Redeploying test Lambda ==="
terraform apply -auto-approve

echo ""
echo "=== Invoking Lambda with $URL ==="
aws lambda invoke \
  --function-name nokogiri-test \
  --payload "{\"url\":\"$URL\"}" \
  --cli-binary-format raw-in-base64-out \
  /tmp/nokogiri-test-out.json

echo ""
cat /tmp/nokogiri-test-out.json | python3 -m json.tool
