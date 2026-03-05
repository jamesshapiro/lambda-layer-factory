#!/usr/bin/env python3
"""Delete cached layer from DynamoDB and S3 so a fresh build is triggered."""

import hashlib
import boto3

# --- Config ---
TABLE_NAME = "layer-factory-ddb"
S3_BUCKET = "layer-factory"

# Must match exactly what the frontend sends
DEPENDENCIES = "nokogiri==1.19.0"
RUNTIMES = ["ruby3.3"]

# --- Compute the cache key (same logic as get_hash.py) ---
deps = sorted(DEPENDENCIES.split(","))
rts = sorted(RUNTIMES)
layer_content = f"{rts}::{deps}"
layer_hash = hashlib.sha256(layer_content.encode()).hexdigest()
print(f"Cache key: {layer_hash}")

ddb = boto3.client("dynamodb")
s3 = boto3.client("s3")

# --- Look up the cached item ---
response = ddb.get_item(TableName=TABLE_NAME, Key={"PK1": {"S": layer_hash}})

if "Item" not in response:
    print("No cache entry found — build should already run fresh.")
else:
    item = response["Item"]
    s3_key = item.get("S3_KEY", {}).get("S", "")
    s3_bucket = item.get("S3_BUCKET", {}).get("S", S3_BUCKET)
    print(f"Found cached item: bucket={s3_bucket} key={s3_key}")

    # Delete S3 object
    if s3_key:
        print(f"Deleting s3://{s3_bucket}/{s3_key}")
        s3.delete_object(Bucket=s3_bucket, Key=s3_key)

    # Delete DynamoDB cache entry
    print(f"Deleting DDB item PK1={layer_hash}")
    ddb.delete_item(TableName=TABLE_NAME, Key={"PK1": {"S": layer_hash}})

    print("Cache busted.")

# --- Also delete any PUBLISH# tokens for this layer ---
scan = ddb.scan(
    TableName=TABLE_NAME,
    FilterExpression="begins_with(PK1, :prefix)",
    ExpressionAttributeValues={":prefix": {"S": "PUBLISH#"}},
)
deleted = 0
for item in scan.get("Items", []):
    if item.get("LAYER_NAME", {}).get("S", "").find("nokogiri") >= 0 or \
       item.get("S3_KEY", {}).get("S", "").find("nokogiri") >= 0:
        pk = item["PK1"]["S"]
        print(f"Deleting publish token: {pk}")
        ddb.delete_item(TableName=TABLE_NAME, Key={"PK1": {"S": pk}})
        deleted += 1

print(f"Deleted {deleted} publish token(s).")
print("\nReady to re-test. Submit a fresh Ruby 3.3 / nokogiri request.")
