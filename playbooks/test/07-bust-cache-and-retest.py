#!/usr/bin/env python3
"""Delete cached layer from DynamoDB and S3 so a fresh build is triggered."""

import sys
import boto3

# --- Config ---
TABLE_NAME = "layer-factory-ddb"
S3_BUCKET = "layer-factory"
SEARCH_TERM = sys.argv[1] if len(sys.argv) > 1 else "nokogiri"

ddb = boto3.client("dynamodb")
s3 = boto3.client("s3")

# --- Scan for any matching entries (cache entries + publish tokens) ---
scan = ddb.scan(TableName=TABLE_NAME)
deleted = 0

for item in scan.get("Items", []):
    pk = item["PK1"]["S"]
    s3_key = item.get("S3_KEY", {}).get("S", "")
    layer_name = item.get("LAYER_NAME", {}).get("S", "")

    if SEARCH_TERM not in s3_key and SEARCH_TERM not in layer_name and SEARCH_TERM not in pk:
        continue

    item_type = "publish token" if pk.startswith("PUBLISH#") else "cache entry"
    print(f"Found {item_type}: PK1={pk}  S3_KEY={s3_key}")

    # Delete S3 object (only for cache entries, not publish tokens)
    if s3_key and not pk.startswith("PUBLISH#"):
        s3_bucket = item.get("S3_BUCKET", {}).get("S", S3_BUCKET)
        print(f"  Deleting s3://{s3_bucket}/{s3_key}")
        s3.delete_object(Bucket=s3_bucket, Key=s3_key)

    # Delete DynamoDB entry
    print(f"  Deleting DDB item PK1={pk}")
    ddb.delete_item(TableName=TABLE_NAME, Key={"PK1": {"S": pk}})
    deleted += 1

print(f"\nDeleted {deleted} item(s) matching '{SEARCH_TERM}'.")
if deleted:
    print("Ready to re-test. Submit a fresh build via demo.lambdalayerfactory.com")
else:
    print("Nothing found — cache is already clean.")
