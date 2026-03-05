#!/bin/bash
set -e

cd ~/code/lambda-layer-factory/test-infra

echo "=== Step 1: Terraform init & apply ==="
terraform init
terraform apply -auto-approve

echo ""
echo "=== Step 2: Invoke the Lambda ==="
aws lambda invoke \
  --function-name nokogiri-test \
  --payload '{"url":"https://example.com"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/nokogiri-test-out.json

echo ""
echo "--- Lambda response ---"
cat /tmp/nokogiri-test-out.json | python3 -m json.tool

echo ""
echo "=== Step 3: Check S3 output ==="
aws s3 ls s3://nokogiri-test-output/ --recursive

echo ""
echo "--- Markdown output ---"
MD_KEY=$(python3 -c "import json; print(json.load(open('/tmp/nokogiri-test-out.json'))['body']['md_key'])")
aws s3 cp "s3://nokogiri-test-output/$MD_KEY" /tmp/nokogiri-test.md
cat /tmp/nokogiri-test.md

echo ""
echo "--- Plaintext output ---"
TXT_KEY=$(python3 -c "import json; print(json.load(open('/tmp/nokogiri-test-out.json'))['body']['txt_key'])")
aws s3 cp "s3://nokogiri-test-output/$TXT_KEY" /tmp/nokogiri-test.txt
cat /tmp/nokogiri-test.txt

echo ""
echo "=== Step 4: Cleanup ==="
echo "Run this when done:"
echo "  cd ~/code/lambda-layer-factory/test-infra && terraform destroy -auto-approve"
