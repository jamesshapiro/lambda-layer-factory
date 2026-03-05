# lambda-layer-factory

Utilities to make it easier to create Lambda Layers

## Validated Runtimes

- **Python**: 3.9, 3.10, 3.11, 3.12, 3.13 (tested with requests)
- **Ruby**: 3.3, 3.4 (tested with Nokogiri)

## Busting the Cache

If you need to force a fresh build (e.g. after a code change), clear the cached entry by search term:

```bash
cd ~/code/lambda-layer-factory/playbooks/test/07-uv-env && uv run 07-bust-cache-and-retest.py [package_name]
```

This scans DynamoDB for cache entries and publish tokens matching the package name, deletes the associated S3 objects, and removes the DynamoDB items.

## Notes

**Ruby + Nokogiri SSL:** If your layer includes Nokogiri, add this environment variable to your Lambda function:

```
SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt
```

Without this, HTTPS requests will fail with `certificate verify failed`.