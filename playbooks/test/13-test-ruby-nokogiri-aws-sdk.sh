#!/bin/bash
set -e

FUNCTION_NAME="nokogiri-aws-sdk-test"
LAYER_ARN="arn:aws:lambda:us-east-1:306468203480:layer:rb-34-nokogiri-aws-sdk-core-lf:1"
ROLE_ARN="arn:aws:iam::306468203480:role/nokogiri-test-lambda-role"
RUNTIME="ruby3.4"
SRC_DIR=~/code/lambda-layer-factory/test-functions/ruby-nokogiri-aws-sdk
ZIP_PATH="/tmp/${FUNCTION_NAME}.zip"
OUT_PATH="/tmp/${FUNCTION_NAME}-out.json"

echo "=== Step 1: Package function ==="
zip -j "$ZIP_PATH" "$SRC_DIR/lambda_function.rb"

echo ""
echo "=== Step 2: Create or update Lambda ==="
if aws lambda get-function --function-name "$FUNCTION_NAME" &>/dev/null; then
  echo "Function exists — updating code and config..."
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_PATH" \
    --output text --query 'FunctionName'
  aws lambda wait function-updated --function-name "$FUNCTION_NAME"
  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --layers "$LAYER_ARN" \
    --output text --query 'FunctionName'
  aws lambda wait function-updated --function-name "$FUNCTION_NAME"
else
  echo "Creating function..."
  aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime "$RUNTIME" \
    --handler lambda_function.lambda_handler \
    --role "$ROLE_ARN" \
    --zip-file "fileb://$ZIP_PATH" \
    --layers "$LAYER_ARN" \
    --timeout 30 \
    --output text --query 'FunctionName'
  aws lambda wait function-active --function-name "$FUNCTION_NAME"
fi

echo ""
echo "=== Step 3: Invoke ==="
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  "$OUT_PATH"

echo ""
echo "--- Response ---"
python3 -m json.tool "$OUT_PATH"

echo ""
echo "=== Cleanup ==="
echo "  aws lambda delete-function --function-name $FUNCTION_NAME"
